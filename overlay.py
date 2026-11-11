from __future__ import annotations

import ctypes
import io
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

import numpy as np
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
MUMU_ROOT = Path(
    os.environ.get(
        "MUMU_ROOT",
        r"D:\TapTap\Support\android_emulator",
    )
)
ADB = MUMU_ROOT / "engine" / "nx_main" / "adb.exe"
DEVICE = os.environ.get("MUMU_ADB", "127.0.0.1:16416")
PACKAGE = "com.puzzle.miniworld.cn"
PLUGIN = ROOT / "plugin.py"
TEMPLATES = [
    ROOT / "assets" / "hint_windmill.png",
    ROOT / "assets" / "hint_kyoto.png",
]
MATCH_THRESHOLD = 0.65
TRANSPARENT_COLOR = "#010203"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run_hidden(arguments: list[str], timeout: float = 4) -> subprocess.CompletedProcess:
    return subprocess.run(
        arguments,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )


def adb(*arguments: str, timeout: float = 4) -> subprocess.CompletedProcess:
    return run_hidden(
        [str(ADB), "-s", DEVICE, *arguments],
        timeout=timeout,
    )


def match_template(
    image: Image.Image,
    template: Image.Image,
) -> tuple[float, tuple[int, int]]:
    image = ImageOps.grayscale(image)
    template = ImageOps.grayscale(template)
    width, height = image.size
    roi_box = (
        int(width * 0.72),
        int(height * 0.02),
        width,
        int(height * 0.46),
    )
    source = np.asarray(template, dtype=np.float64)
    roi = np.asarray(image.crop(roi_box), dtype=np.float64)
    ones = np.ones_like(source)
    count = source.size
    centered_template = source - source.mean()
    template_norm_squared = float((centered_template * centered_template).sum())
    sum_image = fft_correlate(roi, ones)
    sum_image_squared = fft_correlate(roi * roi, ones)
    covariance = fft_correlate(roi, centered_template)
    variance_image = sum_image_squared - sum_image * sum_image / count
    denominator = np.sqrt(
        np.maximum(variance_image * template_norm_squared, 1e-9)
    )
    scores = covariance / denominator
    y, x = np.unravel_index(np.argmax(scores), scores.shape)
    return (
        float(scores[y, x]),
        (roi_box[0] + int(x), roi_box[1] + int(y)),
    )


def fft_correlate(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    shape = (
        image.shape[0] + kernel.shape[0] - 1,
        image.shape[1] + kernel.shape[1] - 1,
    )
    spectrum_image = np.fft.rfft2(image, s=shape)
    spectrum_kernel = np.fft.rfft2(kernel[::-1, ::-1], s=shape)
    result = np.fft.irfft2(spectrum_image * spectrum_kernel, s=shape)
    return result[
        kernel.shape[0] - 1 : image.shape[0],
        kernel.shape[1] - 1 : image.shape[1],
    ]


def detect_hint_button(screenshot: Image.Image) -> tuple[float, tuple[int, int]] | None:
    best: tuple[float, tuple[int, int], tuple[int, int]] | None = None
    for path in TEMPLATES:
        if not path.exists():
            continue
        with Image.open(path) as template:
            candidate = match_template(screenshot, template)
            template_size = template.size
        if best is None or candidate[0] > best[0]:
            best = (candidate[0], candidate[1], template_size)
    if best is None or best[0] < MATCH_THRESHOLD:
        return None
    template_width, template_height = best[2]
    x, y = best[1]
    return best[0], (x + template_width // 2, y + template_height // 2)


class QuickAssemblyOverlay:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.root.configure(bg=TRANSPARENT_COLOR)

        self.expanded = True
        self.busy = False
        self.patch_ready = False
        self.drag_origin: tuple[int, int] | None = None
        self.window_origin: tuple[int, int] | None = None
        self.drag_moved = False
        self.game_misses = 0
        self.closed = False

        self.width = 292
        self.height = 238
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.root.geometry(
            f"{self.width}x{self.height}+{self.screen_width - 340}+120"
        )

        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self._bind_window_drag()
        self._draw_expanded()
        self.root.after(300, self._start_background_sync)
        self.root.after(2500, self._poll_game_state)

    def _rounded_rect(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        radius: int,
        **kwargs,
    ) -> None:
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_expanded(self) -> None:
        self.expanded = True
        self.width, self.height = 292, 238
        self.root.geometry(f"{self.width}x{self.height}")
        self.canvas.configure(
            width=self.width,
            height=self.height,
            bg=TRANSPARENT_COLOR,
        )
        self.canvas.delete("all")
        self._rounded_rect(
            2,
            2,
            self.width - 2,
            self.height - 2,
            18,
            fill="#17222d",
            outline="#2b4657",
            width=1,
        )
        self.canvas.create_text(
            20,
            25,
            anchor="w",
            text="我爱拼模型",
            fill="#f1f5f7",
            font=("Microsoft YaHei UI", 13, "bold"),
        )
        self.canvas.create_text(
            20,
            52,
            anchor="w",
            text="快速拼装助手",
            fill="#8fa9b8",
            font=("Microsoft YaHei UI", 9),
        )
        self._draw_icon_button(
            self.width - 62,
            16,
            "minus",
            "−",
            self.minimize,
        )
        self._draw_icon_button(
            self.width - 32,
            16,
            "close",
            "×",
            self.confirm_exit,
            fill="#d55b5b",
        )
        self._rounded_rect(
            16,
            80,
            self.width - 16,
            148,
            14,
            fill="#31515a",
            outline="#456371",
            width=1,
            tags=("auto_button",),
        )
        self.canvas.create_text(
            self.width // 2,
            114,
            text="自动拼完",
            fill="#ffffff",
            font=("Microsoft YaHei UI", 16, "bold"),
            tags=("auto_button", "auto_text"),
        )
        self.canvas.tag_bind("auto_button", "<Button-1>", self._auto_button_click)
        self.canvas.tag_bind("auto_text", "<Button-1>", self._auto_button_click)
        self.status_id = self.canvas.create_text(
            20,
            174,
            anchor="w",
            text="等待拼装页",
            fill="#9fb3bf",
            font=("Microsoft YaHei UI", 9),
        )
        self.canvas.create_text(
            20,
            202,
            anchor="w",
            text="仅调用游戏原生自动拼接 · 不扣道具",
            fill="#6f8795",
            font=("Microsoft YaHei UI", 8),
        )

    def _draw_icon_button(
        self,
        x: int,
        y: int,
        tag: str,
        text: str,
        command,
        *,
        fill: str = "#233542",
    ) -> None:
        self.canvas.create_oval(
            x,
            y,
            x + 24,
            y + 24,
            fill=fill,
            outline="",
            tags=(tag,),
        )
        self.canvas.create_text(
            x + 12,
            y + 11,
            text=text,
            fill="#ffffff",
            font=("Microsoft YaHei UI", 13, "bold"),
            tags=(tag,),
        )
        self.canvas.tag_bind(tag, "<Button-1>", lambda _event: command())

    def _draw_minimized(self) -> None:
        self.expanded = False
        self.width = self.height = 72
        self.root.geometry(f"72x72")
        self.canvas.configure(width=72, height=72, bg=TRANSPARENT_COLOR)
        self.canvas.delete("all")
        self.canvas.create_oval(
            4,
            4,
            68,
            68,
            fill="#0f766e",
            outline="#2dd4bf",
            width=2,
            tags=("circle",),
        )
        self.canvas.create_text(
            36,
            36,
            text="拼",
            fill="#ffffff",
            font=("Microsoft YaHei UI", 22, "bold"),
            tags=("circle",),
        )

    def _bind_window_drag(self) -> None:
        self.canvas.bind("<ButtonPress-1>", self._begin_drag, add="+")
        self.canvas.bind("<B1-Motion>", self._drag, add="+")
        self.canvas.bind("<ButtonRelease-1>", self._end_drag, add="+")

    def _begin_drag(self, event: tk.Event) -> None:
        self.drag_origin = (event.x_root, event.y_root)
        self.window_origin = (
            self.root.winfo_x(),
            self.root.winfo_y(),
        )
        self.drag_moved = False

    def _drag(self, event: tk.Event) -> None:
        if self.drag_origin is None or self.window_origin is None:
            return
        dx = event.x_root - self.drag_origin[0]
        dy = event.y_root - self.drag_origin[1]
        if abs(dx) + abs(dy) > 4:
            self.drag_moved = True
        self.root.geometry(
            f"+{self.window_origin[0] + dx}+{self.window_origin[1] + dy}"
        )

    def _end_drag(self, event: tk.Event) -> None:
        del event
        if not self.expanded and not self.drag_moved:
            self._draw_expanded()
        self.drag_origin = None
        self.window_origin = None

    def _set_status(self, text: str, color: str = "#9fb3bf") -> None:
        if not self.expanded:
            return
        self.canvas.itemconfigure(self.status_id, text=text, fill=color)

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        if not self.expanded:
            return
        fill = "#31515a" if busy else "#0f766e"
        self.canvas.itemconfigure("auto_button", fill=fill)
        self.canvas.itemconfigure(
            "auto_text",
            text="检测中..." if busy else "自动拼完",
        )

    def _auto_button_click(self, event: tk.Event) -> str:
        del event
        if self.busy:
            return "break"
        if not self.patch_ready:
            self._set_status("版本检测未完成", "#f0b56c")
            return "break"
        self._set_busy(True)
        self._set_status("检测拼装页面...", "#d8e4e8")
        threading.Thread(target=self._run_auto_finish, daemon=True).start()
        return "break"

    def _run_auto_finish(self) -> None:
        ok = False
        message = "请先进入拼装页"
        try:
            ok, message = self._try_auto_finish()
        except Exception:
            ok = False
            message = "ADB 未连接"
        self.root.after(0, lambda: self._finish_auto_attempt(ok, message))

    def _try_auto_finish(self) -> tuple[bool, str]:
        if not ADB.exists():
            return False, "ADB 路径无效"
        try:
            pid_output = adb("shell", "pidof", PACKAGE).stdout.decode(
                errors="ignore"
            ).strip()
        except (subprocess.TimeoutExpired, OSError):
            return False, "ADB 未连接"
        if not pid_output:
            return False, "游戏未运行"

        try:
            activity = adb(
                "shell",
                "dumpsys",
                "activity",
                "activities",
            ).stdout.decode(errors="ignore")
        except (subprocess.TimeoutExpired, OSError):
            return False, "无法读取游戏状态"
        if f"{PACKAGE}/" not in activity:
            return False, "游戏不在前台"

        try:
            shot = adb("exec-out", "screencap", "-p", timeout=6)
        except (subprocess.TimeoutExpired, OSError):
            return False, "截图超时"
        if not shot.stdout.startswith(b"\x89PNG"):
            return False, "无法读取游戏画面"

        with Image.open(io.BytesIO(shot.stdout)) as image:
            match = detect_hint_button(image)
        if match is None:
            return False, "请先进入拼装页"

        _, (x, y) = match
        try:
            adb("shell", "input", "tap", str(x), str(y))
        except (subprocess.TimeoutExpired, OSError):
            return False, "点击发送失败"
        return True, "已触发自动拼完"

    def _finish_auto_attempt(self, ok: bool, message: str) -> None:
        self._set_busy(False)
        self._set_status(
            message,
            "#7dd3c7" if ok else "#f0b56c",
        )
        self.root.after(
            1300 if ok else 900,
            lambda: self._set_status(
                "等待拼装页",
                "#9fb3bf",
            ),
        )

    def _start_background_sync(self) -> None:
        if self.closed:
            return
        threading.Thread(target=self._sync_patch, daemon=True).start()

    def _sync_patch(self) -> None:
        message = ""
        ok = False
        try:
            process = run_hidden(
                [sys.executable, str(PLUGIN), "auto"],
                timeout=90,
            )
            ok = process.returncode == 0
            if not ok:
                text = process.stderr.decode(errors="ignore")
                if "root" in text.lower():
                    message = "请启用调试 root"
                elif "ADB" in text:
                    message = "等待 MuMu"
                else:
                    message = "版本检查失败"
        except (subprocess.TimeoutExpired, OSError):
            message = "等待 MuMu"

        def apply_result() -> None:
            if self.closed or not self.expanded:
                return
            if ok:
                self.patch_ready = True
                self.canvas.itemconfigure(
                    "auto_button",
                    fill="#0f766e",
                    outline="#2dd4bf",
                )
                self._set_status("版本检测完成", "#7dd3c7")
            else:
                self._set_status(message or "版本检查失败", "#f0b56c")

        self.root.after(0, apply_result)

    def _poll_game_state(self) -> None:
        if self.closed:
            return
        try:
            output = adb("shell", "pidof", PACKAGE, timeout=2).stdout
            running = bool(output.strip())
        except (subprocess.TimeoutExpired, OSError):
            running = False
        if running:
            self.game_misses = 0
        else:
            self.game_misses += 1
            if self.game_misses >= 2 and self.expanded:
                self.minimize()
        self.root.after(2500, self._poll_game_state)

    def minimize(self) -> None:
        if not self.expanded or self.busy:
            return
        self._draw_minimized()

    def confirm_exit(self) -> None:
        if messagebox.askyesno(
            "退出插件",
            "是否关闭插件功能？",
            parent=self.root,
        ):
            self.closed = True
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def acquire_single_instance() -> int | None:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(
        None,
        False,
        "Global\\PocketWorldQuickAssemblyOverlay",
    )
    if not handle:
        return None
    if kernel32.GetLastError() == 183:
        return None
    return handle


def main() -> None:
    mutex = acquire_single_instance()
    if mutex is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("我爱拼模型", "快速拼装浮窗已经在运行。")
        root.destroy()
        return
    QuickAssemblyOverlay().run()


if __name__ == "__main__":
    main()
