# What Did I Do — AI Agent Instructions

## Overview
- Purpose: Windows 桌面使用追踪器，记录活跃窗口到按日 CSV，并用可视化查看各进程用时。
- Components: 托盘采集器 [tracker.py](tracker.py) → 每日数据 [data/](data) → 统计图表 [stats.py](stats.py)。
- Platform: Windows-only（依赖 `pywin32`、系统托盘）。GUI 会话必需，WSL 不支持。

## Data Flow & Conventions
- Daily file: [data/YYYY-MM-DD.csv](data)（由 `today_file()` 生成）。
- CSV schema: `start_time, end_time, process, window`。
- Time format: `HH:MM:SS`（本地时间）。
- Write policy: 当活跃窗口或进程变化时，写入一条从上次开始到当前时间的记录；退出时写最后一条。
- Encoding: UTF-8；CSV 由 `csv.writer` 负责转义/引号。
- Sampling: `CHECK_INTERVAL = 2` 秒（可调）。

## Dependencies & Setup
- Dependencies file: [requirments.txt](requirments.txt)（注意：文件名为“requirments”而非“requirements”）。
- Setup:
  - 创建虚拟环境并安装依赖：
    - `python -m venv .venv`
    - `.venv\Scripts\pip install -r requirments.txt`

## Core Workflows
- Run tracker: `python tracker.py`
  - 托盘图标名称为 “WhatDidIDo”。点击菜单的 “Quit” 以停止并刷写最后一条记录。
  - 需要桌面前台权限；前台窗口标题和进程名通过 `win32gui`/`win32process`/`psutil` 获取。
- View stats: `python stats.py`
  - 读取“今天”的 CSV，计算每条 `end_time - start_time` 的秒数，按 `process` 聚合为分钟并绘制柱状图。
  - 空文件或不存在时会报错（`pandas.read_csv` EmptyDataError/文件缺失）；先确保有数据或自行加防护后再运行。

## Project Patterns
- `today_file()` 在两个模块各自实现，统一决定数据路径和文件命名。新增功能请沿用该约定。
- 无 CLI 参数解析：脚本即运行当前日期。若要分析其它日期，建议为 `stats.py` 增加日期参数或文件路径参数（保持默认行为不变）。
- Windows 专用模块请延迟导入或置于特定代码路径，避免非 Windows 环境下导入即失败。

## Extending Examples
- 按窗口标题统计：在 [stats.py](stats.py) 将 `groupby("process")` 改为 `groupby("window")` 或先筛选再聚合。
- 导出图表：在 `plt.show()` 前调用 `plt.savefig("assets/today.png", dpi=200, bbox_inches="tight")`。
- 指定日期：让 `today_file()` 支持可选日期参数，并在 `main()` 中解析 `--date YYYY-MM-DD`。

## Key Files
- Tracker: [tracker.py](tracker.py) — 前台窗口采集、托盘控制、CSV 写入。
- Stats: [stats.py](stats.py) — 读取当日 CSV，计算区间、聚合和可视化。
- Data: [data/](data) — 每日 CSV 存放目录（例：`2025-12-15.csv`）。
- Deps: [requirments.txt](requirments.txt) — 依赖清单（命名有意不同）。
