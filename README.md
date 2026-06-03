# 黄河水情数据工具

从水利部黄河水情日报网站下载数据，整理合并。

数据来源：水利部黄河水利委员会 [黄河水情日报](http://61.163.88.227:8006/hwsq2.aspx?sr=0nkRxv6s9CTRMlwRgmfFF6jTpJPtAv87)

## 工作流

```
每天 14:30（定时任务）
  └── python main.py download
        └── data/raw/2026-06-03.xlsx

每月末（手动运行）
  └── python main.py cleanup --month 2026-06
        └── 自动筛选当月文件 → 增量追加到 data/processed/data2026.xlsx
```

## 安装

```bash
pip install -r requirements.txt
```

## 用法

### 1. 下载数据

从黄河水情日报网站爬取每日站点水位、流量数据。

```bash
# 下载当天（默认）
python main.py download

```

数据保存至 `data/raw/YYYY-MM-DD.xlsx`，每个文件包含当日 15 个黄河干流水文站数据（玛曲、兰州、石嘴山、巴彦高勒、头道拐、吴堡、龙门、华县、潼关、三门峡水库、黑石关、武陟、花园口、高村、泺口、利津）。

> 注意：2024 年底网站改版后不再提供含沙量数据，因此当前仅包含水位和流量。

### 2. 设置定时下载（Windows 任务计划程序）

每天自动下载当天数据：

**步骤 1**：打开任务计划程序（`Win+R` → `taskschd.msc`）

**步骤 2**：创建基本任务
- 名称：`黄河水情每日下载`
- 触发器：**每天**，开始时间 **14:30**
- 操作：**启动程序**

| 字段 | 值 |
|------|-----|
| 程序/脚本 | `...\python.exe`（ Python 完整路径） |
| 参数 | `main.py download` |
| 起始于 | `...\huanghe-water-tools` （完整路径，E:\DATA\huanghe-water-tools）|

> 如果系统提示找不到 `python`，在 cmd 中运行 `where python` 获取完整路径填入"程序/脚本"栏。

**步骤 3**：完成后可右键任务 → **运行** 测试，检查 `data/raw/` 下是否生成了当天的文件。

### 3. 合并数据（增量追加）

月底将当月所有日数据合并到年度总表。

```bash
# 合并当前月份
python main.py cleanup

# 合并指定月份
python main.py cleanup --month 2026-05

# 强制重新合并（忽略已有记录，覆盖重建）
python main.py cleanup --month 2026-05 --force
```

**增量逻辑**：
- 读取 `data/processed/data{year}.xlsx` 中已有的日期
- 仅追加尚未合并的新日期文件
- 多次运行不会重复追加
- 网站偶尔崩溃缺数据，补上后再次运行即可追回

**输出格式**（5 列）：

| 列名 | 说明 | 示例 |
|------|------|------|
| 河名 | 河流名称 | 黄河 |
| 站名 | 水文站名称 | 利津 |
| 水位 | 水位（米） | 9.52 |
| 流量 | 流量（m³/s） | 1310 |
| date | 日期 | 2026-05-31 |

## 数据说明

| 目录 | 内容 | 时间范围 |
|------|------|----------|
| `data/raw/` | 每日下载的原始数据（.xlsx） | 2024-04 ~ 至今 |
| `data/processed/` | 合并后的年度总表（.xlsx） | 2023 ~ 至今 |
| `data/offline/csv/` | 历史 CSV 数据（含含沙量） | 2002 ~ 2022 |
| `data/offline/` | 离线历史压缩包（.zip/.xls） | 2001 ~ 2022 |

- 2023~2024 年基线数据来自已有存档
- 2024.12 后网站改版，不再更新含沙量数据
- 2025 年起数据仅包含水位和流量

## 项目结构

```
huanghe-water-tools/
├── main.py                     # 统一入口
├── requirements.txt
├── .gitignore
├── README.md
├── src/
│   ├── config.py               # 全局配置
│   ├── utils.py                # 工具函数
│   ├── download.py             # 下载模块
 │   └── cleanup.py              # 合并模块（增量追加）
├── data/
│   ├── raw/                    # 原始日数据 *.xlsx
│   ├── processed/              # 合并后年度总表
│   └── offline/
│       ├── csv/                # 历史 CSV 数据（2002-2022）
│       └── (历年压缩包)         # 离线历史数据（2001-2022）
```

## 许可

MIT License
