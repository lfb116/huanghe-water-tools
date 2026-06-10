"""
黄河水情数据合并模块（增量追加）。

从 data/raw/ 读取日数据文件，按月筛选，增量追加到 data/processed/data{year}.xlsx。
输出格式:
    河名, 站名, 水位, 流量, date

用法:
    python -m src.cleanup --month 2026-05
    python -m src.cleanup
    python -m src.cleanup --month 2026-05 --force
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import RAW_DIR, PROCESSED_DIR
from src.utils import setup_logger, month_range, parse_month

logger = setup_logger("cleanup")

TARGET_COLUMNS = ["河名", "站名", "水位", "流量", "date"]


def _read_raw_file(filepath: Path) -> pd.DataFrame:
    df = pd.read_excel(filepath, header=None)
    if df.empty or df.shape[1] < 6:
        return pd.DataFrame()
    data = df.iloc[:, 1:]
    result = pd.DataFrame()
    result["河名"] = data.iloc[:, 0]
    result["站名"] = data.iloc[:, 1]
    result["水位"] = pd.to_numeric(data.iloc[:, 3], errors="coerce")
    result["流量"] = pd.to_numeric(data.iloc[:, 4], errors="coerce")
    return result


def _filename_to_date(filename: str) -> str:
    stem = Path(filename).stem
    try:
        datetime.strptime(stem, "%Y-%m-%d")
        return stem
    except ValueError:
        return ""


def _get_existing_dates(year_file: Path) -> set:
    if not year_file.exists():
        return set()
    try:
        df = pd.read_excel(year_file)
        if "date" not in df.columns:
            return set()
        return set(df["date"].dropna().astype(str).unique())
    except Exception:
        return set()


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame()
    for col in TARGET_COLUMNS:
        if col in df.columns:
            result[col] = df[col]
        else:
            found = False
            for c in df.columns:
                if c.strip() == col:
                    result[col] = df[c]
                    found = True
                    break
            if not found:
                result[col] = None
    for col in ["水位", "流量"]:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors="coerce")
    return result


def _write_year_file(year_file: Path, data: pd.DataFrame, force: bool = False):
    out = data[TARGET_COLUMNS]
    if force or not year_file.exists():
        out.to_excel(year_file, index=False)
        mode = "覆盖" if force else "创建"
        logger.info("已%s %s，写入 %d 行", mode, year_file.name, len(out))
    else:
        existing = _normalize_df(pd.read_excel(year_file))
        combined = pd.concat([existing, out], ignore_index=True)
        combined.to_excel(year_file, index=False)
        logger.info("已追加 %d 行到 %s（原有 %d 行）",
                     len(out), year_file.name, len(existing))


def cleanup_month(month_str: str, force: bool = False) -> int:
    year, _ = parse_month(month_str)
    start_date, end_date = month_range(month_str)
    year_file = PROCESSED_DIR / f"data{year}.xlsx"
    existing_dates = set() if force else _get_existing_dates(year_file)

    if not RAW_DIR.exists():
        logger.error("目录不存在: %s", RAW_DIR)
        return 0

    raw_files = sorted(RAW_DIR.glob("*.xlsx"))
    if not raw_files:
        logger.warning("data/raw/ 下无文件")
        return 0

    matched = []
    for f in raw_files:
        d = _filename_to_date(f.name)
        if d and start_date <= d <= end_date:
            matched.append((d, f))

    if not matched:
        logger.info("在 %s 范围内无文件", month_str)
        return 0

    new_files = [(d, f) for d, f in matched if d not in existing_dates]
    if not new_files:
        logger.info("全部已合并（%d 个）", len(matched))
        return 0

    logger.info("新文件 %d / %d", len(new_files), len(matched))

    rows = []
    for date_str, fp in new_files:
        try:
            df = _read_raw_file(fp)
            if df.empty:
                continue
            df["date"] = date_str
            rows.append(df)
        except Exception as e:
            logger.error("%s 失败: %s", fp.name, e)

    if not rows:
        return 0

    _write_year_file(year_file, pd.concat(rows, ignore_index=True), force=force)
    return len(new_files)


def main():
    parser = argparse.ArgumentParser(description="黄河水情数据合并")
    parser.add_argument("--month", default=None, help="目标月份 YYYY-MM（默认当前）")
    parser.add_argument("--force", action="store_true", help="强制重新合并")
    args = parser.parse_args()

    month_str = args.month or datetime.now().strftime("%Y-%m")
    count = cleanup_month(month_str, args.force)
    logger.info("完成，新增 %d 个文件", count)
    sys.exit(0 if count >= 0 else 1)


if __name__ == "__main__":
    main()
