import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import os
from datetime import datetime

# Local imports
import tracker
import stats

# 状态文件，用于与托盘同步显示
DATA_DIR = os.path.join(os.getcwd(), "data")
STATE_FILE = os.path.join(DATA_DIR, "state.txt")


def read_state() -> str:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            val = f.read().strip().lower()
            if val == "running":
                return "running"
    except Exception:
        pass
    return "stopped"

class TrackerManager:
    def __init__(self):
        self._tracker = None
        self._thread = None
        self._running = False

    def start(self):
        if self._running:
            return
        self._tracker = tracker.Tracker()
        self._running = True
        # 若当天 CSV 不存在或为空，先创建并写入表头
        try:
            tracker.ensure_today_file_with_header()
        except Exception:
            pass
        self._thread = threading.Thread(target=self._tracker.loop, daemon=True)
        self._thread.start()
        try:
            tracker.set_state(True)
        except Exception:
            pass

    def stop(self):
        if not self._running:
            return
        try:
            self._tracker.stop()
        except Exception:
            pass
        self._running = False
        self._tracker = None
        self._thread = None
        try:
            tracker.set_state(False)
        except Exception:
            pass

    @property
    def running(self):
        return self._running


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def on_start(manager: TrackerManager, status_var: tk.StringVar):
    try:
        manager.start()
        status_var.set("状态：记录中…")
    except Exception as e:
        messagebox.showerror("启动失败", str(e))


def on_stop(manager: TrackerManager, status_var: tk.StringVar):
    try:
        manager.stop()
        status_var.set("状态：已停止")
    except Exception as e:
        messagebox.showerror("停止失败", str(e))


def on_view(day_var: tk.StringVar, start_var: tk.StringVar, end_var: tk.StringVar):
    day = day_var.get().strip() or today_str()
    path = os.path.join("data", f"{day}.csv")
    df = stats.load_dataframe(path)
    if df is None:
        return
    start = start_var.get().strip() or None
    end = end_var.get().strip() or None
    minutes = stats.compute_minutes_in_range(df, start, end)
    stats.plot_minutes(minutes, day, save_dir=None, show=True)


def on_save(day_var: tk.StringVar, start_var: tk.StringVar, end_var: tk.StringVar):
    day = day_var.get().strip() or today_str()
    path = os.path.join("data", f"{day}.csv")
    df = stats.load_dataframe(path)
    if df is None:
        return
    start = start_var.get().strip() or None
    end = end_var.get().strip() or None
    minutes = stats.compute_minutes_in_range(df, start, end)

    out_dir = filedialog.askdirectory(title="选择保存目录")
    if not out_dir:
        return
    saved = stats.plot_minutes(minutes, day, save_dir=out_dir, show=False)
    if saved:
        messagebox.showinfo("已保存", f"已保存：{saved}")

def on_view_pie(day_var: tk.StringVar, start_var: tk.StringVar, end_var: tk.StringVar):
    day = day_var.get().strip() or today_str()
    path = os.path.join("data", f"{day}.csv")
    df = stats.load_dataframe(path)
    if df is None:
        return
    start = start_var.get().strip() or None
    end = end_var.get().strip() or None
    minutes = stats.compute_minutes_in_range(df, start, end)
    stats.plot_pie(minutes, day, save_dir=None, show=True)

def on_save_pie(day_var: tk.StringVar, start_var: tk.StringVar, end_var: tk.StringVar):
    day = day_var.get().strip() or today_str()
    path = os.path.join("data", f"{day}.csv")
    df = stats.load_dataframe(path)
    if df is None:
        return
    start = start_var.get().strip() or None
    end = end_var.get().strip() or None
    minutes = stats.compute_minutes_in_range(df, start, end)

    out_dir = filedialog.askdirectory(title="选择保存目录")
    if not out_dir:
        return
    saved = stats.plot_pie(minutes, day, save_dir=out_dir, show=False)
    if saved:
        messagebox.showinfo("已保存", f"已保存：{saved}")


def on_open_data_folder():
    os.makedirs("data", exist_ok=True)
    os.startfile(os.path.abspath("data"))


def on_quit(root: tk.Tk, manager: TrackerManager):
    try:
        manager.stop()
    finally:
        root.destroy()


def main():
    root = tk.Tk()
    root.title("What did I do")
    root.geometry("560x360")

    manager = TrackerManager()

    frm = tk.Frame(root, padx=12, pady=12)
    frm.pack(fill=tk.BOTH, expand=True)

    status_var = tk.StringVar(value="状态：未开始")
    day_var = tk.StringVar(value=today_str())

    # Row 1: status
    tk.Label(frm, textvariable=status_var, anchor="w").pack(fill=tk.X)

    # Row 2: controls
    ctrl = tk.Frame(frm)
    ctrl.pack(fill=tk.X, pady=(8, 0))
    tk.Button(ctrl, text="开始记录", command=lambda: on_start(manager, status_var)).pack(side=tk.LEFT)
    tk.Button(ctrl, text="停止记录", command=lambda: on_stop(manager, status_var)).pack(side=tk.LEFT, padx=6)
    tk.Button(ctrl, text="打开数据文件夹", command=on_open_data_folder).pack(side=tk.RIGHT)

    # Row 3: day & time selection
    row3 = tk.Frame(frm)
    row3.pack(fill=tk.X, pady=(12, 0))
    tk.Label(row3, text="日期 YYYY-MM-DD：").pack(side=tk.LEFT)
    tk.Entry(row3, textvariable=day_var, width=12).pack(side=tk.LEFT)

    # 时间段选择下拉
    time_row = tk.Frame(frm)
    time_row.pack(fill=tk.X, pady=(8, 0))
    tk.Label(time_row, text="选择时间段：").pack(side=tk.LEFT)
    range_var = tk.StringVar(value="全天")
    ranges = [
        "全天",
        "上午 (09:00-12:00)",
        "下午 (13:00-18:00)",
        "晚上 (18:00-23:00)",
        "工作时段 (09:00-18:00)",
        "不限制",
        "自定义…",
    ]
    range_box = tk.OptionMenu(time_row, range_var, *ranges)
    range_box.pack(side=tk.LEFT)

    def range_to_times(sel: str):
        mapping = {
            "全天": (None, None),
            "不限制": (None, None),
            "上午 (09:00-12:00)": ("09:00:00", "12:00:00"),
            "下午 (13:00-18:00)": ("13:00:00", "18:00:00"),
            "晚上 (18:00-23:00)": ("18:00:00", "23:00:00"),
            "工作时段 (09:00-18:00)": ("09:00:00", "18:00:00"),
        }
        return mapping.get(sel, (None, None))

    # 自定义输入框（默认禁用）
    # 自定义时间：开始时间行
    custom_row_start = tk.Frame(frm)
    custom_row_start.pack(fill=tk.X, pady=(6, 0))
    tk.Label(custom_row_start, text="开始时间 HH:MM:SS：").pack(side=tk.LEFT)
    start_var = tk.StringVar(value="")
    start_e = tk.Entry(custom_row_start, textvariable=start_var, width=10)
    start_e.pack(side=tk.LEFT)

    # 自定义时间：结束时间行（单独一行更美观）
    custom_row_end = tk.Frame(frm)
    custom_row_end.pack(fill=tk.X, pady=(4, 0))
    tk.Label(custom_row_end, text="结束时间 HH:MM:SS：").pack(side=tk.LEFT)
    end_var = tk.StringVar(value="")
    end_e = tk.Entry(custom_row_end, textvariable=end_var, width=10)
    end_e.pack(side=tk.LEFT)
    # 初始禁用
    start_e.configure(state="disabled")
    end_e.configure(state="disabled")

    def on_range_change(*_):
        if range_var.get() == "自定义…":
            start_e.configure(state="normal")
            end_e.configure(state="normal")
        else:
            start_e.configure(state="disabled")
            end_e.configure(state="disabled")
            start_var.set("")
            end_var.set("")
    range_var.trace_add("write", on_range_change)

    def get_selected_times():
        sel = range_var.get()
        if sel == "自定义…":
            s = start_var.get().strip() or None
            e = end_var.get().strip() or None
            return s, e
        return range_to_times(sel)

    # Row 4: stats buttons
    row4 = tk.Frame(frm)
    row4.pack(fill=tk.X, pady=(12, 0))
    tk.Button(row4, text="查看图表", command=lambda: on_view(day_var, tk.StringVar(value=get_selected_times()[0]), tk.StringVar(value=get_selected_times()[1]))).pack(side=tk.LEFT)
    tk.Button(row4, text="保存图表…", command=lambda: on_save(day_var, tk.StringVar(value=get_selected_times()[0]), tk.StringVar(value=get_selected_times()[1]))).pack(side=tk.LEFT, padx=6)
    tk.Button(row4, text="查看饼图", command=lambda: on_view_pie(day_var, tk.StringVar(value=get_selected_times()[0]), tk.StringVar(value=get_selected_times()[1]))).pack(side=tk.LEFT, padx=6)
    tk.Button(row4, text="保存饼图…", command=lambda: on_save_pie(day_var, tk.StringVar(value=get_selected_times()[0]), tk.StringVar(value=get_selected_times()[1]))).pack(side=tk.LEFT)

    def refresh_status():
        st = read_state()
        if st == "running":
            status_var.set("状态：记录中…")
        else:
            # 若本地 manager 在运行但状态文件未更新，也显示记录中
            status_var.set("状态：记录中…" if manager.running else "状态：未开始")
        root.after(1000, refresh_status)

    refresh_status()
    root.protocol("WM_DELETE_WINDOW", lambda: on_quit(root, manager))
    root.mainloop()


if __name__ == "__main__":
    main()
