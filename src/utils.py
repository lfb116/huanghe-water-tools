"""
通用工具函数：日志、目录、日期解析等。
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def setup_logger(name: str = "huanghe", level: int = logging.INFO) -> logging.Logger:
    """配置并返回带控制台输出的 logger。"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    return logger


def ensure_dir(path: Path) -> Path:
    """确保目录存在，返回该目录路径。"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_month(month_str: str) -> tuple[int, int]:
    """解析 'YYYY-MM' 格式字符串，返回 (year, month)。"""
    try:
        dt = datetime.strptime(month_str, "%Y-%m")
        return dt.year, dt.month
    except ValueError as e:
        raise ValueError(f"月份格式错误，应为 YYYY-MM，收到：{month_str!r}") from e


def month_range(month_str: str) -> tuple[str, str]:
    """根据 'YYYY-MM' 返回该月首日和末日字符串 ('YYYY-MM-DD', 'YYYY-MM-DD')。"""
    year, month = parse_month(month_str)
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def current_month_str() -> str:
    """返回当前月份字符串 'YYYY-MM'。"""
    return datetime.now().strftime("%Y-%m")


def filename_to_date(filename: str) -> Optional[str]:
    """
    从文件名提取日期 'YYYY-MM-DD'。
    支持 '2026-05-01.xlsx', '2026-05-01.xls' 等格式。
    返回 'YYYY-MM-DD' 或 None（无法解析时）。
    """
    stem = Path(filename).stem  # 去掉扩展名
    try:
        dt = datetime.strptime(stem, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None
