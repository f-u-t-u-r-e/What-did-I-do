import time
import os
import csv
from datetime import datetime

import win32gui
import win32process
import psutil
import win32api

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import threading
import sys
import atexit
import ctypes
import subprocess
import stats


CHECK_INTERVAL = 2  # 每 2 秒检测一次窗口变化
DATA_DIR = "data"
STATE_FILE = os.path.join(DATA_DIR, "state.txt")


def _file_description(path: str) -> str | None:
    try:
        info = win32api.GetFileVersionInfo(path, "\\")
        # 遍历所有可用的语言/代码页，优先 FileDescription
        translations = win32api.VerQueryValue(info, r"\VarFileInfo\Translation") or []
        for lang, codepage in translations:
            for key in ("FileDescription", "ProductName"):
                sub_block = f"\StringFileInfo\\{lang:04X}{codepage:04X}\\{key}"
                val = win32api.VerQueryValue(info, sub_block)
                if val:
                    s = str(val).strip()
                    if s:
                        return s
        # 常见回退语言：0409-04B0 / 0409-04E4（英语-美国）
        common = [
            (0x0409, 0x04B0),
            (0x0409, 0x04E4),
        ]
        for lang, codepage in common:
            for key in ("FileDescription", "ProductName"):
                sub_block = f"\StringFileInfo\\{lang:04X}{codepage:04X}\\{key}"
                try:
                    val = win32api.VerQueryValue(info, sub_block)
                except Exception:
                    val = None
                if val:
                    s = str(val).strip()
                    if s:
                        return s
    except Exception:
        pass
    return None


def get_active_window():
    hwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    process = psutil.Process(pid)
    exe = None
    try:
        exe = process.exe()
    except Exception:
        exe = None
    app = _file_description(exe) if exe else None
    app_name = app or process.name()
    if not app:
        # 针对常见进程名提供更友好的名称映射
        name_map = {
            "Code.exe": "Visual Studio Code",
            "msedge.exe": "Microsoft Edge",
            "chrome.exe": "Google Chrome",
            "explorer.exe": "文件资源管理器",
            "python.exe": "Python",
        }
        app_name = name_map.get(process.name(), process.name())
    return app_name, win32gui.GetWindowText(hwnd)


def today_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    name = datetime.now().strftime("%Y-%m-%d") + ".csv"
    return os.path.join(DATA_DIR, name)


def set_state(running: bool):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write("running" if running else "stopped")
    except Exception:
        pass


def ensure_today_file_with_header():
    """确保今天的 CSV 文件存在且有表头。"""
    try:
        path = today_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        need_header = True
        if os.path.exists(path):
            try:
                need_header = os.path.getsize(path) == 0
            except OSError:
                need_header = True
        if (not os.path.exists(path)) or need_header:
            with open(path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["start_time", "end_time", "process", "window"])
    except Exception:
        pass


def write_record(start, end, process, window):
    path = today_file()
    exists = os.path.exists(path)
    need_header = True
    if exists:
        try:
            need_header = os.path.getsize(path) == 0
        except OSError:
            need_header = True

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not exists or need_header:
            writer.writerow(["start_time", "end_time", "process", "window"])
        writer.writerow([start, end, process, window])


class Tracker:
    def __init__(self):
        self.running = False
        self.last_process = None
        self.last_window = None
        self.last_start_time = None

    def loop(self):
        while self.running:
            try:
                process, window = get_active_window()
                now = datetime.now().strftime("%H:%M:%S")

                if (process != self.last_process) or (window != self.last_window):
                    if self.last_process is not None:
                        write_record(
                            self.last_start_time,
                            now,
                            self.last_process,
                            self.last_window,
                        )

                    self.last_process = process
                    self.last_window = window
                    self.last_start_time = now

                time.sleep(CHECK_INTERVAL)
            except Exception:
                time.sleep(CHECK_INTERVAL)

    def stop(self):
        self.running = False
        now = datetime.now().strftime("%H:%M:%S")
        if self.last_process:
            write_record(
                self.last_start_time,
                now,
                self.last_process,
                self.last_window,
            )


def create_image():
    image = Image.new("RGB", (64, 64), color=(30, 30, 30))
    d = ImageDraw.Draw(image)
    d.rectangle((16, 16, 48, 48), fill=(0, 200, 255))
    return image


def main():
    tracker = Tracker()
    # 初始不启动记录线程，等待用户点击“开始记录”
    # 启动时将状态初始化为未记录
    try:
        set_state(False)
    except Exception:
        pass

    def quit_app(icon, item):
        try:
            tracker.stop()
        except Exception:
            pass
        try:
            set_state(False)
        except Exception:
            pass
        icon.stop()
        sys.exit(0)

    def notify(msg: str, title: str = "What did I do"):
        # 在后台线程中显示系统模态、置顶并前置的消息框，避免阻塞托盘事件循环
        def _worker():
            try:
                ctypes.windll.user32.MessageBoxW(
                    None,
                    msg,
                    title,
                    (
                        0x00000000  # MB_OK
                        | 0x00001000  # MB_SYSTEMMODAL
                        | 0x00010000  # MB_SETFOREGROUND
                        | 0x00040000  # MB_TOPMOST
                    ),
                )
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def start_tracking(icon, item):
        if tracker.running:
            return
        try:
            tracker.running = True
            tracker.last_process = None
            tracker.last_window = None
            tracker.last_start_time = None
            # 若当天文件不存在，则立即创建并写入表头，避免“未开始前无文件”的情况
            ensure_today_file_with_header()
            threading.Thread(target=tracker.loop, daemon=True).start()
            set_state(True)
            notify("已开始记录。")
        except Exception:
            notify("启动记录失败")

    def stop_tracking(icon, item):
        try:
            tracker.stop()
            set_state(False)
            notify("已停止记录。")
        except Exception:
            notify("停止记录失败")

    def clear_today(icon, item):
        def worker():
            day = datetime.now().strftime("%Y-%m-%d")
            path = stats.today_file(day)
            # 使用原生消息框，系统模态并置顶，避免与托盘事件循环冲突
            try:
                res = ctypes.windll.user32.MessageBoxW(
                    None,
                    f"将删除今日数据文件:\n{os.path.abspath(path)}\n\n确定要删除吗？",
                    "确认删除",
                    (
                        0x00000001  # MB_OKCANCEL
                        | 0x00000030  # MB_ICONWARNING
                        | 0x00001000  # MB_SYSTEMMODAL
                        | 0x00010000  # MB_SETFOREGROUND
                        | 0x00040000  # MB_TOPMOST
                    ),
                )
                if res != 1:
                    return
            except Exception:
                # 无法弹窗则默认执行
                pass

            try:
                # 统一处理：若存在则清空并重置表头；若不存在则创建空文件含表头
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["start_time", "end_time", "process", "window"])

                # 重置当前跟踪状态，避免立刻写入旧区间
                try:
                    # 访问外部作用域的 tracker 对象
                    nonlocal tracker
                    tracker.last_process = None
                    tracker.last_window = None
                    tracker.last_start_time = None
                except Exception:
                    pass

                # 将状态标记为已清空，若未运行则保持 stopped
                set_state(tracker.running)

                notify("已清空今日数据。")
            except Exception:
                notify("删除数据失败。")

        threading.Thread(target=worker, daemon=True).start()

    def open_gui(icon, item):
        try:
            frozen = getattr(sys, "frozen", False)
            base_dir = os.path.dirname(sys.executable) if frozen else os.getcwd()
            parent_dir = os.path.dirname(base_dir)
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
            except Exception:
                script_dir = None

            candidates = []
            # 优先同目录/上级目录的 GUI EXE（免环境，推荐同时打包到 dist）
            candidates.append(os.path.join(base_dir, "WhatDidIDo.exe"))
            candidates.append(os.path.join(parent_dir, "WhatDidIDo.exe"))
            # 源码路径（开发场景）
            if script_dir:
                candidates.append(os.path.join(script_dir, "dist", "WhatDidIDo.exe"))
                candidates.append(os.path.join(script_dir, "WhatDidIDo.exe"))
                candidates.append(os.path.join(script_dir, "app.pyw"))
                candidates.append(os.path.join(script_dir, "app.py"))

            for p in candidates:
                path = os.path.normpath(p)
                if os.path.exists(path):
                    try:
                        if path.lower().endswith(".exe"):
                            os.startfile(path)
                        elif path.lower().endswith(".pyw"):
                            # 优先使用文件关联启动（无控制台）
                            try:
                                os.startfile(path)
                            except Exception:
                                subprocess.Popen([sys.executable, path], creationflags=0x00000008)
                        else:
                            subprocess.Popen([sys.executable, path], creationflags=0x00000008)
                        return
                    except Exception:
                        continue
            notify("未找到可用的 GUI 程序。请先构建 GUI（dist/WhatDidIDo.exe），或在项目根目录保留 app.pyw。")
        except Exception:
            notify("打开 GUI 失败。")

    icon = pystray.Icon(
        "What did I do",
        create_image(),
        menu=pystray.Menu(
            item("开始记录", start_tracking),
            item("停止记录", stop_tracking),
            item("清除今日数据", clear_today),
            item("打开图形界面", open_gui),
            item("打开数据文件夹", lambda _i, _it: os.startfile(os.path.abspath(DATA_DIR))),
            pystray.Menu.SEPARATOR,
            item("退出", quit_app),
        ),
    )

    # 确保进程退出时刷写最后一条
    atexit.register(tracker.stop)

    try:
        icon.run()
    except KeyboardInterrupt:
        tracker.stop()
        try:
            icon.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
