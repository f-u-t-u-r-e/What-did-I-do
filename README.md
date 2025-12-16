# What Did I Do (Windows)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![GUI](https://img.shields.io/badge/Tkinter-UI-yellow)
![Tray](https://img.shields.io/badge/pystray-Tray-lightgrey)
![Version](https://img.shields.io/badge/Version-2.0-brightgreen)
![License](https://img.shields.io/badge/License-MIT-orange)

## 项目简介

Windows 桌面使用追踪器：记录今日前台窗口使用区间到按日 CSV，并生成“今日时间分布图”（柱状图/饼图）。包含系统托盘采集器与可视化脚本，适合自我时间管理与简单分析。

## 主要功能

- 活跃窗口追踪（开始/停止/退出自动刷写最后一条）
- 每日 CSV 存档（`start_time,end_time,process,window`）
- 进程用时统计（分钟，按 `process` 聚合；可切换 `window`）
- 可视化（柱状图/饼图），支持保存 PNG 到 `assets/`
- 时间段过滤（`--start/--end`），总用时打印
- 托盘与 GUI 状态同步（`data/state.txt`）

## 新增亮点（v2.0）

- GUI：时间段预设/自定义，查看/保存柱状图与饼图
- 字体与美化：中文字体、网格、标签旋转与右对齐、DPI 提升
- 容错：缺文件/空文件/无表头自动回退并提示
- 启动体验：开始记录时自动创建 CSV 表头；托盘提示改为后台线程系统模态

## 技术栈

- 编程语言：Python 3.10+
- 图形界面：Tkinter（`app.pyw`）
- 系统托盘：pystray（`tracker.py`）
- 数据分析与绘图：pandas / matplotlib（可选 mplcursors）
- 进程与窗口：pywin32 / psutil / win32gui / win32process

## 运行环境

- 操作系统：Windows（需 GUI 会话），WSL 不支持
- Python：3.10 及以上版本
- 编码：UTF-8（CSV 由 `csv.writer` 负责转义/引号）
- 字体建议：系统需中文字体（微软雅黑/黑体），已在绘图中优先配置

## 项目结构

```
what-did-i-do/
├── start.cmd                   # 一键启动（托盘+GUI）
├── README.md                   # 项目说明（本文件）
├── requirments.txt             # 依赖
├── tracker.py                  # 托盘采集器：记录窗口区间
├── stats.py                    # 统计与可视化（柱状图/饼图）
├── app.pyw                     # GUI
└── data/                       # 每日 CSV（例：2025-12-15.csv）
```

## 数据文件说明

每日文件：`data/YYYY-MM-DD.csv`

```
# start_time,end_time,process,window
09:00:01,09:30:12,chrome,Project Docs - Google Drive
09:30:12,09:58:47,Code.exe,main.py - VS Code
```

约定：
- 写入策略：窗口或进程变化时写上一段；退出时补全最后一条
- 时间格式：`HH:MM:SS`（本地时间）
- 采样：`CHECK_INTERVAL = 2` 秒（可在 `tracker.py` 修改）

## 安装与运行

方式一：虚拟环境（推荐）
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r .\requirments.txt
.\.venv\Scripts\python tracker.py
.\.venv\Scripts\python app.pyw   # 可选 GUI
.\.venv\Scripts\python stats.py --save assets
```

方式二：系统 Python
```powershell
python -m pip install -r .\requirments.txt
python tracker.py
python app.pyw                     # 可选 GUI
python stats.py --start 09:00:00 --end 12:00:00 --pie --save assets
```

方式三：一键脚本
```bat
start.cmd
```
说明：脚本优先使用 `.venv\Scripts\pythonw.exe`，回退到系统 `pythonw/python`；后台启动托盘，前台启动 GUI。

## 使用说明

1. 启动托盘：运行 `tracker.py`，在托盘菜单选择 Start/Stop/Clear Today/Open GUI/Open Data/ Quit
2. 统计今天：运行 `stats.py --save assets` 保存柱状图；或 `--pie` 保存饼图
3. 指定时间段：`stats.py --start 13:00:00 --end 15:30:00`（总用时会在控制台打印）
4. GUI 交互：运行 `app.pyw`，在下拉框选择预设或自定义起止时间后查看/保存图表

## 常见问题 FAQ

| 问题 | 可能原因 | 解决方法 |
|------|----------|----------|
| `start.cmd` 运行后 GUI 未出现 | `.pyw` 关联异常或依赖未安装 | 先安装依赖；分别运行 `python tracker.py` 与 `python app.pyw` 检查报错；脚本已强制用 `pythonw/python` 启动 |
| 托盘“开始记录”后无数据 | 当天 CSV 尚未创建或空文件 | 托盘/GUI 开始时自动创建并写入表头；也可先手动运行一次 `tracker.py` |
| GUI 显示“未开始”但托盘已开始 | 状态不同步 | 使用 `data/state.txt` 同步；托盘与 GUI 已统一写入/读取该文件 |
| 中文显示为方块/负号异常 | 系统中文字体不可用或 matplotlib 未配置 | 已设置中文字体与 `axes.unicode_minus=False`；安装中文字体后重试 |
| `stats.py` 报空/列缺失 | CSV 无表头或为空 | 已做容错；确保列为 `start_time,end_time,process,window` |
| PowerShell 脚本受限 | 执行策略限制 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 后重试 |

## 更新日志

### v2.0 (2025-12)
- GUI 支持时间段选择（预设/自定义），查看/保存柱状图与饼图
- 开始记录自动创建当日 CSV 表头；托盘提示改为后台线程系统模态
- 图表美化与中文字体配置；标签自动换行、右对齐与 30° 旋转
- 统计 CLI：`--start/--end`、`--pie`、总用时输出；空文件/无表头容错
- 托盘与 GUI 状态同步（`data/state.txt`）

### v1.x
- 初版：采集 `start_time,end_time,process,window` 到每日 CSV；基础可视化

## 未来规划

- 更丰富的交互提示（mplcursors）与导出模板
- 系统通知（toast）替代消息框，减少打断
- 指定日期管理工具与批量清理
- 一键诊断脚本（记录启动错误与依赖检查）

## 贡献

欢迎：
- 提交 Issue / Bug 报告
- 追加应用名映射与本地化
- 优化 UI/交互与数据结构
- 增加自动化测试

## 免责声明 / 许可

本项目遵循 MIT 许可证。数据文件由使用者自行维护；不保证用于真实生产环境的稳定性。

联系方式

- Issues：反馈问题与建议
- Discussions：功能讨论与扩展

---

如果需要英文版或进一步的功能文档，请提出需求。
- **开发时间**: 2025.12

## 许可

本项目采用 MIT 许可证，允许用于商业与非商业用途，需保留版权与许可声明。
