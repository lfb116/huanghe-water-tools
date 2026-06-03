"""
黄河水情数据工具 - 全局配置

所有路径、URL、默认参数集中管理，模块通过导入本模块获取配置。
"""

import os
from pathlib import Path

# ── 项目根目录（自动检测） ──────────────────────────────────────
# 假设 config.py 位于 src/config.py，项目根目录是其父目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── 数据目录 ────────────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"           # 原始下载的日数据 *.xlsx
PROCESSED_DIR = DATA_DIR / "processed"  # 合并后的年度总表
OFFLINE_DIR = DATA_DIR / "offline"      # 2001-2022 离线历史数据
OFFLINE_CSV_DIR = OFFLINE_DIR / "csv"   # 历史 CSV 数据（2002-2022）

# ── 下载配置 ────────────────────────────────────────────────────
WATER_INFO_URL = (
    "http://61.163.88.227:8006/hwsq2.aspx"
    "?sr=0nkRxv6s9CTRMlwRgmfFF6jTpJPtAv87"
)

REQUEST_TIMEOUT = 30  # 单次请求超时（秒）
REQUEST_RETRIES = 3   # 失败重试次数
REQUEST_RETRY_DELAY = 2  # 重试间隔（秒）

# ── 自动创建目录 ────────────────────────────────────────────────
for _dir in [RAW_DIR, PROCESSED_DIR, OFFLINE_DIR, OFFLINE_CSV_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)
