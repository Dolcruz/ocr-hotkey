from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import logging
import os
import sys
import threading
import traceback
import winsound
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
LOG_PATH = APP_DIR / "ocr-hotkey.log"
LAST_CAPTURE_PATH = APP_DIR / "last_capture.png"
DEFAULT_HOTKEY = "<ctrl>+<alt>+<shift>+o"
MIN_SELECTION_PX = 6


def set_window_bounds(window: Any, left: int, top: int, width: int, height: int) -> None:
    window.geometry(f"{width}x{height}")
    window.update_idletasks()
    frame_id = window.tk.call("wm", "frame", window._w)
    hwnd_value = int(frame_id, 0) if isinstance(frame_id, str) else int(frame_id)
    hwnd = wintypes.HWND(hwnd_value)
    swp_noactivate = 0x0010
    swp_showwindow = 0x0040
    hwnd_topmost = wintypes.HWND(-1)
    user32 = ctypes.windll.user32
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    ok = user32.SetWindowPos(
        hwnd,
        hwnd_topmost,
        int(left),
        int(top),
        int(width),
        int(height),
        swp_noactivate | swp_showwindow,
    )
    if not ok:
        logging.warning("SetWindowPos failed for hwnd=%s target=(%s,%s,%s,%s)", hwnd_value, left, top, width, height)
    rect = wintypes.RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        logging.debug(
            "Overlay window hwnd=%s target=(%s,%s,%s,%s) actual=(%s,%s,%s,%s)",
            hwnd_value,
            left,
            top,
            width,
            height,
            rect.left,
            rect.top,
            rect.right - rect.left,
            rect.bottom - rect.top,
        )


def make_dpi_aware() -> None:
    try:
        awareness_context = ctypes.c_void_p(-4 & 0xFFFFFFFFFFFFFFFF)
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(awareness_context):
            return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def setup_logging() -> None:
    handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[handler],
    )


def ensure_single_instance() -> int | None:
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.CreateMutexW(None, False, "Local\\FalkOcrHotkey")
        if handle and ctypes.get_last_error() == 183:
            logging.info("Another OCR hotkey instance is already running; exiting.")
            sys.exit(0)
        return handle
    except Exception:
        logging.exception("Could not create single-instance mutex")
        return None


class OcrEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ocr: Any | None = None

    def load(self) -> Any:
        with self._lock:
            if self._ocr is not None:
                return self._ocr

            os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "huggingface")
            os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
            logging.info("Loading PaddleOCR PP-OCRv6 model")
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(
                text_detection_model_name="PP-OCRv6_medium_det",
                text_recognition_model_name="PP-OCRv6_medium_rec",
                engine="transformers",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
            logging.info("PaddleOCR model loaded")
            return self._ocr

    def read_image(self, image_path: Path) -> str:
        ocr = self.load()
        results = ocr.predict(str(image_path))
        return extract_text(results)


def extract_text(results: Any) -> str:
    lines: list[str] = []

    def add_text(value: Any) -> bool:
        added = False
        if isinstance(value, str):
            text = value.strip()
            if text:
                lines.append(text)
                return True
            return False
        if isinstance(value, (list, tuple)):
            for item in value:
                added = add_text(item) or added
        return added

    def to_mapping(value: Any) -> dict[str, Any] | None:
        if isinstance(value, dict):
            return value
        for attr in ("to_dict", "json"):
            member = getattr(value, attr, None)
            if member is None:
                continue
            try:
                data = member() if callable(member) else member
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
        if hasattr(value, "__dict__"):
            return vars(value)
        return None

    result_items = results if isinstance(results, list) else [results]
    for result in result_items:
        data = to_mapping(result)
        if not data:
            continue
        for key in ("rec_texts", "texts", "text"):
            if key in data and add_text(data[key]):
                break

    return "\n".join(lines)


def capture_region(region: tuple[int, int, int, int], output_path: Path = LAST_CAPTURE_PATH) -> Path:
    import mss
    from PIL import Image

    left, top, width, height = region
    monitor = {"left": left, "top": top, "width": width, "height": height}
    with mss.MSS() as screen:
        shot = screen.grab(monitor)
    image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    image.save(output_path)
    return output_path


class SelectionOverlay:
    def __init__(self, root: Any, on_selection: Any) -> None:
        import mss
        import tkinter as tk

        self.root = root
        self.on_selection = on_selection
        self.start_x = 0
        self.start_y = 0
        self.overlays: list[dict[str, Any]] = []

        with mss.MSS() as screen:
            monitors = list(screen.monitors[1:] or screen.monitors[:1])

        for monitor in monitors:
            left = int(monitor["left"])
            top = int(monitor["top"])
            width = int(monitor["width"])
            height = int(monitor["height"])

            window = tk.Toplevel(root)
            window.overrideredirect(True)
            window.attributes("-topmost", True)
            window.attributes("-alpha", 0.35)
            window.configure(bg="black")
            set_window_bounds(window, left, top, width, height)

            canvas = tk.Canvas(
                window,
                bg="black",
                highlightthickness=0,
                cursor="crosshair",
            )
            canvas.pack(fill="both", expand=True)
            canvas.create_text(
                18,
                18,
                anchor="nw",
                fill="white",
                text="Drag OCR region. Esc cancels.",
                font=("Segoe UI", 14),
            )
            rect_id = canvas.create_rectangle(0, 0, 0, 0, outline="white", width=2, state="hidden")

            overlay = {
                "window": window,
                "canvas": canvas,
                "left": left,
                "top": top,
                "width": width,
                "height": height,
                "rect_id": rect_id,
            }
            self.overlays.append(overlay)

            canvas.bind("<ButtonPress-1>", self.on_press)
            canvas.bind("<B1-Motion>", self.on_drag)
            canvas.bind("<ButtonRelease-1>", self.on_release)
            window.bind("<B1-Motion>", self.on_drag)
            window.bind("<ButtonRelease-1>", self.on_release)
            window.bind("<Escape>", self.cancel)
            window.bind("<Button-3>", self.cancel)
            window.lift()

        if self.overlays:
            first_window = self.overlays[0]["window"]
            first_window.focus_force()

    def on_press(self, event: Any) -> None:
        window = event.widget.winfo_toplevel()
        try:
            window.grab_set_global()
        except Exception:
            window.grab_set()
        self.start_x = int(event.x_root)
        self.start_y = int(event.y_root)
        self._update_rectangles(self.start_x, self.start_y)

    def on_drag(self, event: Any) -> None:
        self._update_rectangles(int(event.x_root), int(event.y_root))

    def on_release(self, event: Any) -> None:
        end_x = int(event.x_root)
        end_y = int(event.y_root)
        x1, x2 = sorted((self.start_x, end_x))
        y1, y2 = sorted((self.start_y, end_y))
        regions = self._selected_regions(x1, y1, x2, y2)
        self.close()
        if not regions:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            return
        self.root.after(120, lambda: self.on_selection(regions))

    def _update_rectangles(self, end_x: int, end_y: int) -> None:
        x1, x2 = sorted((self.start_x, end_x))
        y1, y2 = sorted((self.start_y, end_y))
        for overlay in self.overlays:
            left = overlay["left"]
            top = overlay["top"]
            right = left + overlay["width"]
            bottom = top + overlay["height"]
            clip_x1 = max(x1, left)
            clip_y1 = max(y1, top)
            clip_x2 = min(x2, right)
            clip_y2 = min(y2, bottom)
            canvas = overlay["canvas"]
            rect_id = overlay["rect_id"]
            if clip_x2 <= clip_x1 or clip_y2 <= clip_y1:
                canvas.itemconfigure(rect_id, state="hidden")
                continue
            canvas.itemconfigure(rect_id, state="normal")
            canvas.coords(rect_id, clip_x1 - left, clip_y1 - top, clip_x2 - left, clip_y2 - top)

    def _selected_regions(self, x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int, int, int]]:
        regions: list[tuple[int, int, int, int]] = []
        for overlay in self.overlays:
            left = overlay["left"]
            top = overlay["top"]
            right = left + overlay["width"]
            bottom = top + overlay["height"]
            clip_x1 = max(x1, left)
            clip_y1 = max(y1, top)
            clip_x2 = min(x2, right)
            clip_y2 = min(y2, bottom)
            width = clip_x2 - clip_x1
            height = clip_y2 - clip_y1
            if width >= MIN_SELECTION_PX and height >= MIN_SELECTION_PX:
                regions.append((clip_x1, clip_y1, width, height))
        return sorted(regions, key=lambda item: (item[0], item[1]))

    def cancel(self, _event: Any = None) -> None:
        self.close()

    def close(self) -> None:
        for overlay in self.overlays:
            window = overlay["window"]
            try:
                window.grab_release()
            except Exception:
                pass
            window.destroy()
        self.overlays = []


class OcrHotkeyApp:
    def __init__(self, hotkey: str, preload: bool) -> None:
        import tkinter as tk

        self.hotkey = hotkey
        self.preload = preload
        self.engine = OcrEngine()
        self.busy = False
        self.root = tk.Tk()
        self.root.withdraw()

    def run(self) -> int:
        from pynput import keyboard

        logging.info("Starting OCR hotkey listener: %s", self.hotkey)
        if self.preload:
            threading.Thread(target=self._preload_model, daemon=True).start()

        listener = keyboard.GlobalHotKeys({self.hotkey: self._hotkey_pressed})
        listener.start()
        try:
            self.root.mainloop()
        finally:
            listener.stop()
        return 0

    def _preload_model(self) -> None:
        try:
            self.engine.load()
        except Exception:
            logging.exception("OCR model preload failed")

    def _hotkey_pressed(self) -> None:
        self.root.after(0, self._start_selection)

    def _start_selection(self) -> None:
        if self.busy:
            self._message("OCR is still running")
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            return
        SelectionOverlay(self.root, self._process_selection)

    def _process_selection(self, regions: list[tuple[int, int, int, int]]) -> None:
        self.busy = True
        self._message("OCR running...")
        threading.Thread(target=self._worker, args=(regions,), daemon=True).start()

    def _worker(self, regions: list[tuple[int, int, int, int]]) -> None:
        try:
            text_parts: list[str] = []
            for index, region in enumerate(regions, start=1):
                output_path = LAST_CAPTURE_PATH if index == 1 else APP_DIR / f"last_capture_{index}.png"
                image_path = capture_region(region, output_path)
                text = self.engine.read_image(image_path)
                if text:
                    text_parts.append(text)
            text = "\n".join(text_parts)
            if text:
                import pyperclip

                pyperclip.copy(text)
                logging.info("Copied %s OCR characters to clipboard", len(text))
                self.root.after(0, lambda: self._message(f"Copied {len(text)} chars"))
                winsound.MessageBeep(winsound.MB_OK)
            else:
                logging.info("No OCR text found")
                self.root.after(0, lambda: self._message("No text found"))
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            logging.error("OCR selection failed:\n%s", traceback.format_exc())
            self.root.after(0, lambda: self._message("OCR failed; see log"))
            winsound.MessageBeep(winsound.MB_ICONHAND)
        finally:
            self.busy = False

    def _message(self, message: str, duration_ms: int = 1400) -> None:
        import mss
        import tkinter as tk

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg="#202124")
        label = tk.Label(
            popup,
            text=message,
            bg="#202124",
            fg="white",
            font=("Segoe UI", 10),
            padx=14,
            pady=8,
        )
        label.pack()
        popup.update_idletasks()

        with mss.MSS() as screen:
            monitor = screen.monitors[1] if len(screen.monitors) > 1 else screen.monitors[0]

        x = int(monitor["left"] + monitor["width"] - popup.winfo_width() - 24)
        y = int(monitor["top"] + monitor["height"] - popup.winfo_height() - 72)
        set_window_bounds(popup, x, y, popup.winfo_width(), popup.winfo_height())
        popup.after(duration_ms, popup.destroy)


def ocr_image_once(image_path: Path) -> int:
    text = OcrEngine().read_image(image_path)
    if text:
        print(text)
        return 0
    print("")
    return 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Global screen-region OCR hotkey")
    parser.add_argument("--hotkey", default=DEFAULT_HOTKEY, help="pynput hotkey syntax")
    parser.add_argument("--no-preload", action="store_true", help="load OCR model on first use")
    parser.add_argument("--ocr-image", type=Path, help="OCR one image and print the result")
    return parser.parse_args()


def main() -> int:
    make_dpi_aware()
    setup_logging()
    args = parse_args()
    if args.ocr_image:
        return ocr_image_once(args.ocr_image)

    mutex = ensure_single_instance()
    _ = mutex
    app = OcrHotkeyApp(args.hotkey, preload=not args.no_preload)
    return app.run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        setup_logging()
        logging.error("Fatal startup failure:\n%s", traceback.format_exc())
        raise
