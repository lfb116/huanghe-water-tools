#!/usr/bin/env python3
"""
黄河水情数据工具 — 统一入口

子命令:
    download    下载水情日报数据
    cleanup     合并数据到年度总表（增量追加）
    cleanup     合并数据到年度总表（增量追加）

用法:
    python main.py download --start 2026-06-01 --end 2026-06-03
    python main.py cleanup --month 2026-05
    python main.py --help
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="黄河水情数据工具 — 下载 · 合并 · 分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── download ──────────────────────────────────────────────
    dl_parser = subparsers.add_parser(
        "download", help="下载水情日报数据",
        description="从水利部黄河水情日报网站下载数据",
    )
    dl_parser.add_argument("--start", help="起始日期 YYYY-MM-DD（默认今天）")
    dl_parser.add_argument("--end", help="截止日期 YYYY-MM-DD（默认今天）")
    dl_parser.add_argument("--output-dir", default=None, help="输出目录")

    # ── cleanup ──────────────────────────────────────────────
    cl_parser = subparsers.add_parser(
        "cleanup", help="合并数据到年度总表（增量追加）",
        description=(
            "将 data/raw/ 中指定月份的数据合并追加到年度总表 data/processed/data{year}.xlsx。\n"
            "自动跳过已合并的日期。"
        ),
    )
    cl_parser.add_argument(
        "--month", default=None,
        help="目标月份 YYYY-MM（默认当前月份）",
    )
    cl_parser.add_argument(
        "--force", action="store_true",
        help="强制重新合并已有日期的文件",
    )

    args = parser.parse_args()

    if args.command == "download":
        from src.download import Downloader
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        downloader = Downloader(output_dir=args.output_dir)
        count = downloader.download_date_range(
            start=args.start or today,
            end=args.end or today,
        )
        print(f"\n✅ 下载完成，成功 {count} 个文件")

    elif args.command == "cleanup":
        from src.cleanup import cleanup_month
        from datetime import datetime
        month_str = args.month or datetime.now().strftime("%Y-%m")
        count = cleanup_month(month_str, force=args.force)
        print(f"\n✅ 合并完成，新增文件数: {count}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
