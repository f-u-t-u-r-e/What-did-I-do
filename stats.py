import argparse
import os
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from pandas.errors import EmptyDataError
from matplotlib import rcParams
import textwrap
from typing import Dict, List, Tuple


def today_file(date_str: str | None = None):
    if date_str:
        name = date_str + ".csv"
    else:
        name = datetime.now().strftime("%Y-%m-%d") + ".csv"
    return os.path.join("data", name)


def time_to_seconds(t):
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s


def parse_args():
    p = argparse.ArgumentParser(description="WhatDidIDo — 今日时间分布图")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--date", help="分析指定日期 YYYY-MM-DD（默认今天）")
    g.add_argument("--file", help="直接指定 CSV 文件路径")
    p.add_argument("--save", nargs="?", const="assets", default=None, help="保存图到目录（可选：目录路径，默认 assets）")
    p.add_argument("--start", help="起始时间 HH:MM:SS（可选）")
    p.add_argument("--end", help="结束时间 HH:MM:SS（可选）")
    p.add_argument("--pie", action="store_true", help="生成饼形图显示比例（默认柱状图）")
    return p.parse_args()


def resolve_path(args) -> tuple[str, str]:
    if args.file:
        path = args.file
        day = os.path.splitext(os.path.basename(path))[0]
    else:
        day = args.date if args.date else datetime.now().strftime("%Y-%m-%d")
        path = today_file(day)
    return path, day

def load_dataframe(path: str) -> pd.DataFrame | None:
    if not os.path.exists(path):
        print(f"No data file: {path}")
        return None

    try:
        df = pd.read_csv(path, encoding="utf-8")
    except EmptyDataError:
        print(f"Data file is empty: {path}")
        return None

    if df.empty:
        print(f"No rows to summarize in: {path}")
        return None

    required = {"start_time", "end_time", "process"}
    missing = required - set(df.columns)
    if missing:
        # 回退：尝试将其视为无表头 CSV
        try:
            df2 = pd.read_csv(
                path,
                header=None,
                names=["start_time", "end_time", "process", "window"],
                encoding="utf-8",
            )
            df = df2
        except Exception:
            pass

    missing = required - set(df.columns)
    if missing:
        print(f"Missing required columns: {', '.join(sorted(missing))}")
        return None

    return df

def compute_minutes(df: pd.DataFrame) -> pd.Series:
    if "duration" not in df.columns:
        df["duration"] = df.apply(
            lambda r: time_to_seconds(r["end_time"]) - time_to_seconds(r["start_time"]),
            axis=1,
        )
    summary = df.groupby("process")["duration"].sum().sort_values(ascending=False)
    minutes = summary / 60
    return minutes

def compute_minutes_in_range(df: pd.DataFrame, start: str | None, end: str | None) -> pd.Series:
    """按给定时间区间裁剪每条记录，仅统计与区间重叠的部分时长（分钟），并按进程聚合。"""
    if start is None and end is None:
        return compute_minutes(df)

    start_s = time_to_seconds(start) if start else 0
    end_s = time_to_seconds(end) if end else 24 * 3600

    rows = []
    for _, r in df.iterrows():
        s = time_to_seconds(r["start_time"])
        e = time_to_seconds(r["end_time"])
        if e < s:
            continue
        # 计算与区间 [start_s, end_s] 的重叠部分
        overlap_s = max(s, start_s)
        overlap_e = min(e, end_s)
        if overlap_e > overlap_s:
            rows.append((r["process"], (overlap_e - overlap_s) / 60.0))

    if not rows:
        return pd.Series(dtype=float)
    agg = {}
    for proc, mins in rows:
        agg[proc] = agg.get(proc, 0.0) + mins
    return pd.Series(agg).sort_values(ascending=False)

def compute_minutes_by_hour(df: pd.DataFrame) -> Dict[str, List[Tuple[int, float]]]:
    """按小时聚合每个进程的用时（分钟）。返回 {process: [(hour, minutes), ...]}。
    小时取 start_time 所在小时，以记录跨度拆分到跨越的各小时桶。
    """
    # 先确保有 duration
    if "duration" not in df.columns:
        df["duration"] = df.apply(
            lambda r: time_to_seconds(r["end_time"]) - time_to_seconds(r["start_time"]),
            axis=1,
        )

    buckets: Dict[str, Dict[int, float]] = {}
    for _, row in df.iterrows():
        start_s = time_to_seconds(row["start_time"])  # 秒
        end_s = time_to_seconds(row["end_time"])      # 秒
        proc = str(row["process"])
        if end_s < start_s:
            # 容错：若时间倒序，跳过
            continue
        if proc not in buckets:
            buckets[proc] = {}

        # 将区间拆分到每个小时边界（以本地当天 0 点为起点）
        cur = start_s
        while cur < end_s:
            hour_start = (cur // 3600) * 3600
            hour_end = hour_start + 3600
            seg_end = min(end_s, hour_end)
            seg_minutes = (seg_end - cur) / 60.0
            hour = int(hour_start // 3600)
            buckets[proc][hour] = buckets[proc].get(hour, 0.0) + seg_minutes
            cur = seg_end

    # 排序并转换为列表
    result: Dict[str, List[Tuple[int, float]]] = {}
    for proc, hm in buckets.items():
        # 过滤掉接近 0 的值并按小时排序
        items = [(h, m) for h, m in sorted(hm.items()) if m > 0.01]
        result[proc] = items
    return result

def plot_minutes(
    minutes: pd.Series,
    day: str,
    save_dir: str | None = None,
    show: bool = True,
    block: bool = True,
) -> str | None:
    if minutes.empty:
        print("No durations to plot.")
        return None

    # 应用名友好映射与自动换行
    friendly_map = {
        # 浏览器与通用
        "Code.exe": "Visual Studio Code",
        "chrome.exe": "Google Chrome",
        "msedge.exe": "Microsoft Edge",
        "firefox.exe": "Mozilla Firefox",
        "explorer.exe": "文件资源管理器",
        "notepad.exe": "记事本",
        "cmd.exe": "命令提示符",
        "powershell.exe": "Windows PowerShell",
        "WindowsTerminal.exe": "Windows Terminal",
        "python.exe": "Python",
        "git.exe": "Git",

        # Office 与效率
        "WINWORD.EXE": "Microsoft Word",
        "EXCEL.EXE": "Microsoft Excel",
        "POWERPNT.EXE": "Microsoft PowerPoint",
        "OUTLOOK.EXE": "Microsoft Outlook",
        "notion.exe": "Notion",
        "obsidian.exe": "Obsidian",
        "Typora.exe": "Typora",

        # 即时通信与协作
        "WeChat.exe": "微信",
        "QQ.exe": "QQ",
        "TIM.exe": "TIM",
        "DingTalk.exe": "钉钉",
        "WeCom.exe": "企业微信",
        "slack.exe": "Slack",
        "Teams.exe": "Microsoft Teams",

        # 开发工具
        "idea64.exe": "IntelliJ IDEA",
        "pycharm64.exe": "PyCharm",
        "clion64.exe": "CLion",
        "rider64.exe": "Rider",
        "devenv.exe": "Visual Studio",

        # 设计与多媒体
        "Photoshop.exe": "Adobe Photoshop",
        "Illustrator.exe": "Adobe Illustrator",
        "AfterFX.exe": "Adobe After Effects",
        "Premiere.exe": "Adobe Premiere Pro",
        "Audition.exe": "Adobe Audition",
        "blender.exe": "Blender",
        "vlc.exe": "VLC",
        "potplayer.exe": "PotPlayer",
        "mpv.exe": "MPV",
        "AppleMusic.exe":"Apple Music",
        "Xmind.exe":"Xmind",

        # 游戏与平台
        "steam.exe": "Steam",
        "Battle.net.exe": "Battle.net",
        "RiotClientServices.exe": "Riot 客户端",
        "LeagueClient.exe": "英雄联盟",
        "wegame.exe":"Wegame",

        # 远程与邮件
        "mstsc.exe": "远程桌面",
        "thunderbird.exe": "Thunderbird",

        # 版本控制与客户端
        "GitHubDesktop.exe": "GitHub Desktop",
        "SourceTree.exe": "Sourcetree",
        "Fork.exe": "Fork",

        # 压缩与文件
        "7zFM.exe": "7-Zip",
        "WinRAR.exe": "WinRAR",

        # 系统与服务
        "explorer.exe": "Windows 桌面/文件管理器",
        "svchost.exe": "系统服务宿主",
        "services.exe": "服务管理器",
        "lsass.exe": "本地安全机构",
        "winlogon.exe": "登录管理",
        "csrss.exe": "客户端/服务器运行时",
        "taskmgr.exe": "任务管理器",
        "System": "内核进程",

        # 安全与云盘等国产软件
        "360safe.exe": "360 安全卫士",
        "ZhuDongFangYu.exe": "360 主动防御",
        "360tray.exe": "360 托盘",
        "baidunetdisk.exe": "百度网盘",
        "AliyunDrive.exe": "阿里云盘",
        "Tencentdl.exe": "腾讯下载器",
        "Thunder.exe": "迅雷",
        "wpscloudsvr.exe": "WPS 云服务",
        "HuorongTray.exe": "火绒托盘",
        "HuorongDaemon.exe": "火绒后台",

        # 多媒体与直播
        "vlc.exe": "VLC 播放器",
        "potplayer.exe": "PotPlayer",
        "QQMusic.exe": "QQ 音乐",
        "cloudmusic.exe": "网易云音乐",
        "iTunes.exe": "iTunes",
        "obs64.exe": "OBS Studio",

        # 游戏平台
        "steam.exe": "Steam",
        "EpicGamesLauncher.exe": "Epic 游戏平台",

        #工具
        "clash-verge.exe":"Clash Verge"
    }

    def format_label(name: str, width: int = 14) -> str:
        label = friendly_map.get(str(name), str(name))
        return "\n".join(textwrap.wrap(label, width=width, break_long_words=True))

    # 原始索引保留用于悬停映射
    original_index = list(minutes.index)
    minutes.index = [format_label(x) for x in original_index]

    # 设置中文字体与美化样式
    try:
        rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Segoe UI", "Arial"]
        rcParams["axes.unicode_minus"] = False
    except Exception:
        pass

    plt.figure(figsize=(10, 6))
    ax = minutes.plot(kind="bar", color="#4C9EEB")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.set_xlabel("应用")
    ax.set_ylabel("分钟")
    ax.set_title(f"今日时间分布 — {day}")
    ax.tick_params(axis="x", labelrotation=30)
    for tick in ax.get_xticklabels():
        tick.set_horizontalalignment("right")
    plt.tight_layout()

    # 悬停提示：显示该应用在各小时的用时分布
    hover_annotation = None
    try:
        # 为悬停显示准备映射（使用原始进程名）
        # 需要原始 DataFrame 来计算小时分布；尝试从调用方上下文获取最近加载的数据不现实
        # 因此这里通过读取当天文件再计算（与主流程一致）。
        df_path = today_file(day)
        df_hover = load_dataframe(df_path)
        per_hour = compute_minutes_by_hour(df_hover) if df_hover is not None else {}

        # 进程名映射到友好标签后的文本，建立从绘图标签到原进程名的反向映射
        label_to_proc = {}
        for orig, lbl in zip(original_index, minutes.index):
            label_to_proc[str(lbl)] = str(orig)

        def format_hours(proc: str) -> str:
            hours = per_hour.get(proc)
            if not hours:
                return "无小时分布数据"
            parts = []
            for h, m in hours:
                parts.append(f"{h:02d}:00-{h:02d}:59：{m:.1f} 分钟")
            return "\n".join(parts)

        def on_move(event):
            nonlocal hover_annotation
            if event.inaxes != ax:
                if hover_annotation:
                    hover_annotation.set_visible(False)
                    ax.figure.canvas.draw_idle()
                return
            # 命中测试：找到靠近鼠标的柱子
            for rect, lbl in zip(ax.patches, minutes.index):
                contains, _ = rect.contains(event)
                if contains:
                    proc = label_to_proc.get(str(lbl), str(lbl))
                    text = format_hours(proc)
                    x = rect.get_x() + rect.get_width() / 2
                    y = rect.get_height()
                    if hover_annotation is None:
                        hover_annotation = ax.annotate(
                            text,
                            xy=(x, y),
                            xytext=(20, 20),
                            textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w", ec="#999", alpha=0.9),
                            arrowprops=dict(arrowstyle="->", color="#666"),
                            fontsize=9,
                        )
                    else:
                        hover_annotation.set_text(text)
                        hover_annotation.xy = (x, y)
                        hover_annotation.set_visible(True)
                    ax.figure.canvas.draw_idle()
                    break
            else:
                if hover_annotation:
                    hover_annotation.set_visible(False)
                    ax.figure.canvas.draw_idle()

        ax.figure.canvas.mpl_connect("motion_notify_event", on_move)
    except Exception:
        # 悬停提示非关键功能，忽略异常以避免影响绘图
        pass

    saved_path = None
    if save_dir is not None:
        out_dir = save_dir if save_dir else "assets"
        os.makedirs(out_dir, exist_ok=True)
        saved_path = os.path.join(out_dir, f"{day}.png")
        plt.savefig(saved_path, dpi=220, bbox_inches="tight")
        print(f"Saved figure: {saved_path}")

    if show:
        try:
            plt.show(block=block)
        except TypeError:
            # 兼容旧版 Matplotlib 无 block 参数
            plt.show()
        if not block:
            try:
                # 确保窗口渲染一次
                plt.pause(0.001)
            except Exception:
                pass
    return saved_path

def plot_pie(
    minutes: pd.Series,
    day: str,
    save_dir: str | None = None,
    show: bool = True,
    block: bool = True,
) -> str | None:
    if minutes.empty:
        print("No durations to plot.")
        return None

    # 字体设置
    try:
        rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Segoe UI", "Arial"]
        rcParams["axes.unicode_minus"] = False
    except Exception:
        pass

    labels = list(minutes.index)
    values = list(minutes.values)
    plt.figure(figsize=(8, 8))
    patches, texts, autotexts = plt.pie(
        values,
        labels=labels,
        autopct=lambda p: f"{p:.1f}%",
        startangle=90,
        counterclock=False,
        wedgeprops={"linewidth": 1, "edgecolor": "white"},
        textprops={"fontsize": 10},
    )
    plt.title(f"应用使用比例 — {day}")
    plt.tight_layout()

    saved_path = None
    if save_dir is not None:
        out_dir = save_dir if save_dir else "assets"
        os.makedirs(out_dir, exist_ok=True)
        saved_path = os.path.join(out_dir, f"{day}_pie.png")
        plt.savefig(saved_path, dpi=220, bbox_inches="tight")
        print(f"Saved pie: {saved_path}")

    if show:
        try:
            plt.show(block=block)
        except TypeError:
            plt.show()
        if not block:
            try:
                plt.pause(0.001)
            except Exception:
                pass
    return saved_path


def main():
    args = parse_args()
    path, day = resolve_path(args)

    df = load_dataframe(path)
    if df is None:
        return 0

    minutes = compute_minutes_in_range(df, args.start, args.end)
    total = float(minutes.sum()) if not minutes.empty else 0.0
    if args.start or args.end:
        print(f"区间用时总计：{total:.1f} 分钟")
    else:
        print(f"今日用时总计：{total:.1f} 分钟")

    save_dir = args.save if args.save is not None else None
    if args.pie:
        plot_pie(minutes, day, save_dir=save_dir, show=True)
    else:
        plot_minutes(minutes, day, save_dir=save_dir, show=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
