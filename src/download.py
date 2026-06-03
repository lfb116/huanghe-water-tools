"""
黄河水情日报数据下载模块。

从水利部黄河水情日报网站爬取每日站点水位、流量、含沙量数据。
网站基于 ASP.NET WebForm，需要先获取 __VIEWSTATE 等隐藏字段再提交查询。

用法:
    python -m src.download --start 2026-06-01 --end 2026-06-03
    python -m src.download                       # 仅下载当天
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

import bs4
import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.config import WATER_INFO_URL, REQUEST_TIMEOUT, REQUEST_RETRIES, REQUEST_RETRY_DELAY, RAW_DIR
from src.utils import setup_logger, ensure_dir

logger = setup_logger("download")

# ── HTTP 请求头 ─────────────────────────────────────────────────
HEADER_INITIAL = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Host": "61.163.88.227:8006",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
    ),
}

HEADER_QUERY = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Host": "61.163.88.227:8006",
    "Origin": "http://61.163.88.227:8006",
    "Referer": WATER_INFO_URL,
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
    ),
}


class Downloader:
    """黄河水情日报下载器。"""

    def __init__(self, output_dir=None):
        self.session = requests.Session()
        self.output_dir = ensure_dir(output_dir or RAW_DIR)
        self.postdata: dict = {"sr": "0nkRxv6s9CTRMlwRgmfFF6jTpJPtAv87"}

    # ── 公共方法 ────────────────────────────────────────────────

    def download_date_range(self, start: str, end: str) -> int:
        """
        下载指定日期范围内的所有水情日报。

        参数:
            start: 起始日期 'YYYY-MM-DD'
            end:   截止日期 'YYYY-MM-DD'

        返回:
            成功下载的文件数
        """
        date_list = self._generate_date_list(start, end)
        if not date_list:
            logger.warning("日期范围无效: %s ~ %s", start, end)
            return 0

        # 第一步：建立会话，获取隐藏表单字段
        if not self._init_session():
            logger.error("初始化会话失败，终止下载")
            return 0

        success_count = 0
        for date_str in date_list:
            try:
                if self._download_single(date_str):
                    success_count += 1
            except Exception as e:
                logger.error("%s 下载异常: %s", date_str, e)

        logger.info(
            "下载完成: 成功 %d / 总计 %d", success_count, len(date_list)
        )
        return success_count

    # ── 内部方法 ────────────────────────────────────────────────

    def _generate_date_list(self, start: str, end: str) -> list[str]:
        """生成日期字符串列表。"""
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
        except ValueError as e:
            logger.error("日期格式错误 (应为 YYYY-MM-DD): %s", e)
            return []

        if start_dt > end_dt:
            logger.error("起始日期晚于截止日期")
            return []

        dates = []
        cur = start_dt
        while cur <= end_dt:
            dates.append(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)
        return dates

    def _init_session(self) -> bool:
        """首次访问页面，获取 ASP.NET 隐藏字段。"""
        for attempt in range(1, REQUEST_RETRIES + 1):
            try:
                resp = self.session.post(
                    WATER_INFO_URL, headers=HEADER_INITIAL, timeout=REQUEST_TIMEOUT
                )
                if resp.status_code != 200:
                    logger.warning(
                        "初始化返回 %d (尝试 %d/%d)",
                        resp.status_code, attempt, REQUEST_RETRIES,
                    )
                    time.sleep(REQUEST_RETRY_DELAY)
                    continue

                resp.encoding = resp.apparent_encoding
                self._extract_postdata(resp.text)
                logger.info("会话初始化成功")
                return True

            except requests.RequestException as e:
                logger.warning(
                    "网络错误: %s (尝试 %d/%d)", e, attempt, REQUEST_RETRIES
                )
                time.sleep(REQUEST_RETRY_DELAY)

        return False

    def _extract_postdata(self, html: str):
        """从 HTML 中提取 __VIEWSTATE 等隐藏表单字段。"""
        needed = {
            "__VIEWSTATE", "__VIEWSTATEGENERATOR",
            "__EVENTVALIDATION", "TextBox11", "Button2",
        }
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("input"):
            if not isinstance(tag, bs4.element.Tag):
                continue
            name = tag.attrs.get("name")
            value = tag.attrs.get("value", "")
            if name in needed and value:
                self.postdata[name] = value

    def _download_single(self, date_str: str) -> bool:
        """下载单日数据。"""
        out_path = self.output_dir / f"{date_str}.xlsx"
        if out_path.exists():
            logger.info("%s 已存在，跳过", date_str)
            return True

        self.postdata["TextBox11"] = date_str

        for attempt in range(1, REQUEST_RETRIES + 1):
            try:
                resp = self.session.post(
                    WATER_INFO_URL,
                    headers=HEADER_QUERY,
                    data=self.postdata,
                    timeout=REQUEST_TIMEOUT,
                )
                if resp.status_code != 200:
                    logger.warning(
                        "%s 返回 %d (尝试 %d/%d)",
                        date_str, resp.status_code, attempt, REQUEST_RETRIES,
                    )
                    time.sleep(REQUEST_RETRY_DELAY)
                    continue

                resp.encoding = resp.apparent_encoding
                text = resp.text

                # 检测空页面
                if "error" in text and len(text) < 38:
                    logger.warning("%s 返回空页面，跳过", date_str)
                    return False

                rows = self._parse_table(text)
                if len(rows) < 2:
                    logger.warning("%s 未能解析到数据行", date_str)
                    return False

                df = pd.DataFrame(rows[1:], columns=rows[0])
                df.to_excel(out_path, index=True)
                logger.info("%s 下载成功 (%d 行)", date_str, len(df))
                return True

            except requests.RequestException as e:
                logger.warning(
                    "%s 网络错误: %s (尝试 %d/%d)",
                    date_str, e, attempt, REQUEST_RETRIES,
                )
                time.sleep(REQUEST_RETRY_DELAY)

        logger.error("%s 下载失败（已达最大重试次数）", date_str)
        return False

    def _parse_table(self, html: str) -> list[list[str]]:
        """解析 HTML 中的水情表格，返回二维列表。"""
        soup = BeautifulSoup(html, "html.parser")
        rows_out = []

        for row_idx, tr in enumerate(soup.find_all("tr")):
            # 原逻辑：只有 5 个子元素的 tr 才是有效数据行
            if len(tr) != 5:
                continue
            first_td = tr.contents[0]
            if not isinstance(first_td, bs4.element.Tag):
                continue

            row_data = []
            for col_idx, td in enumerate(tr.contents):
                if not isinstance(td, bs4.element.Tag):
                    continue
                cell = td.contents[0] if td.contents else ""

                # 第一行第一列是 '河名'，内容直接是字符串
                if row_idx == 0 and col_idx == 0:
                    row_data.append(str(cell))
                elif isinstance(cell, bs4.element.Tag):
                    inner = cell.contents
                    row_data.append(str(inner[0]) if inner else "")
                else:
                    row_data.append(str(cell))

            if row_data:
                rows_out.append(row_data)

        return rows_out


# ── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="黄河水情日报数据下载",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  download --start 2026-06-01 --end 2026-06-03\n"
            "  download                          # 仅下载当天\n"
            "  download --output-dir ./my_data   # 指定输出目录\n"
        ),
    )
    parser.add_argument("--start", help="起始日期 YYYY-MM-DD（默认今天）")
    parser.add_argument("--end", help="截止日期 YYYY-MM-DD（默认今天）")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="输出目录（默认 data/raw）",
    )
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    start = args.start or today
    end = args.end or today

    downloader = Downloader(output_dir=args.output_dir)
    count = downloader.download_date_range(start, end)
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
