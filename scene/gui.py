"""Standalone Tkinter desktop window viewer for the Cozy Christmas Living Room."""

from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING

from .palette import RGB
from .renderer import _PlaybackState

if TYPE_CHECKING:
    import tkinter as tk
    from .canvas import Canvas
    from .renderer import LivingRoomRenderer

_WINDOW_BG = "#0e0c10"
_KEY_MAP = {
    "space": " ",
    "return": "\r",
    "kp_enter": "\r",
    "escape": "escape",
    "q": "q",
    "l": "l",
    "r": "r",
}


def compute_scale(
    avail_w: int,
    avail_h: int,
    px_w: int,
    px_h: int,
    min_scale: int = 2,
    max_scale: int = 14,
) -> int:
    """Return the largest integer sub-pixel zoom factor fitting inside avail_w x avail_h."""
    if px_w <= 0 or px_h <= 0:
        return min_scale
    fit = min(avail_w // px_w, avail_h // px_h)
    return max(min_scale, min(max_scale, fit))


def rgb_to_hex(rgb: RGB) -> str:
    """Format an (r, g, b) tuple as a Tk #rrggbb color string."""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def dirty_row_span(prev_rows: list[bytes] | None, curr_rows: list[bytes]) -> tuple[int, int] | None:
    """Return the inclusive-exclusive [y0, y1) sub-pixel row slice that changed, or None."""
    height = len(curr_rows)
    if height == 0:
        return None
    if prev_rows is None or len(prev_rows) != height:
        return 0, height

    first: int | None = None
    last = 0
    for y in range(height):
        if curr_rows[y] != prev_rows[y]:
            if first is None:
                first = y
            last = y + 1
    return None if first is None else (first, last)


def _enable_windows_dpi_awareness() -> None:
    """Enable per-monitor/system DPI awareness on Windows so pixel art stays razor-sharp."""
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _pick_mono_family(tkfont_mod: object) -> str:
    """Select a crisp monospace font family available on the current OS."""
    families = set(tkfont_mod.families())
    for candidate in ("Consolas", "Cascadia Mono", "DejaVu Sans Mono", "Menlo", "Courier New"):
        if candidate in families:
            return candidate
    return "TkFixedFont"


class LivingRoomWindow:
    """Interactive Tkinter window rendering the sub-pixel buffer and glyph overlay."""

    def __init__(self, root: "tk.Tk", renderer: "LivingRoomRenderer") -> None:
        import tkinter as tk
        import tkinter.font as tkfont

        self._tk = tk
        self._root = root
        self._renderer = renderer
        self._px_w = renderer.WIDTH
        self._px_h = renderer.HEIGHT * 2
        self._frame_dt = 1.0 / renderer.fps

        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        self._scale = compute_scale(
            int(screen_w * 0.88),
            int(screen_h * 0.84),
            self._px_w,
            self._px_h,
            min_scale=4,
            max_scale=12,
        )
        self._offset_x = 0
        self._offset_y = 0

        win_w = self._px_w * self._scale
        win_h = self._px_h * self._scale
        pos_x = max(0, (screen_w - win_w) // 2)
        pos_y = max(0, (screen_h - win_h) // 2)

        root.title("Cozy Christmas Living Room")
        root.configure(bg=_WINDOW_BG)
        root.minsize(self._px_w * 4, self._px_h * 4)
        root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")

        self._canvas = tk.Canvas(
            root,
            width=win_w,
            height=win_h,
            bg=_WINDOW_BG,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack(fill="both", expand=True)

        self._dest_photo = tk.PhotoImage(width=win_w, height=win_h)
        self._image_id = self._canvas.create_image(0, 0, anchor="nw", image=self._dest_photo)

        family = _pick_mono_family(tkfont)
        font_px = self._font_pixel_size(self._scale)
        self._font_regular = tkfont.Font(root=root, family=family, size=font_px, weight="normal")
        self._font_bold = tkfont.Font(root=root, family=family, size=font_px, weight="bold")

        self._prev_rows: list[bytes] | None = None
        self._glyph_items: dict[tuple[int, int], tuple[int, tuple[str, RGB, bool]]] = {}
        self._after_id: str | None = None
        self._closed = False
        self._last_canvas_size = (win_w, win_h)

        if not renderer.skip_intro:
            renderer.warmup()
        self._state = _PlaybackState.create(time.monotonic(), renderer.skip_intro, renderer.intro_speed)

        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<KeyPress>", self._on_key)
        root.bind("<Control-c>", lambda _evt: self.close())
        self._canvas.bind("<Configure>", self._on_configure)

    @staticmethod
    def _font_pixel_size(scale: int) -> int:
        """Compute negative pixel height so glyph labels fit inside a (scale x 2*scale) cell."""
        return -max(8, int(scale * 1.45))

    def start(self) -> None:
        """Focus the window, draw the initial frame, and start the animation loop."""
        self._root.lift()
        self._root.focus_set()
        self._tick()
        self._root.mainloop()

    def close(self) -> None:
        """Cancel pending frame callbacks and destroy the Tkinter window cleanly."""
        if self._closed:
            return
        self._closed = True
        if self._after_id is not None:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self._root.destroy()

    def _on_key(self, event: "tk.Event") -> None:
        if self._closed or (getattr(event, "state", 0) & 0x4):
            return
        keysym = event.keysym.lower()
        key = _KEY_MAP.get(keysym)
        if key is None and event.char:
            key = event.char.lower()
        now = time.monotonic()
        if self._state.handle_key(key, now, self._renderer):
            self.close()
            return
        if key in ("l", "r", " ", "\r", "\n"):
            self.render_step(now)

    def _on_configure(self, event: "tk.Event") -> None:
        if self._closed or (event.width, event.height) == self._last_canvas_size:
            return
        self._last_canvas_size = (event.width, event.height)
        new_scale = compute_scale(event.width, event.height, self._px_w, self._px_h)
        new_ox = max(0, (event.width - self._px_w * new_scale) // 2)
        new_oy = max(0, (event.height - self._px_h * new_scale) // 2)

        scale_changed = new_scale != self._scale
        self._scale = new_scale
        self._offset_x = new_ox
        self._offset_y = new_oy
        self._canvas.coords(self._image_id, new_ox, new_oy)

        if scale_changed:
            self._dest_photo = self._tk.PhotoImage(
                width=self._px_w * new_scale,
                height=self._px_h * new_scale,
            )
            self._canvas.itemconfigure(self._image_id, image=self._dest_photo)
            font_px = self._font_pixel_size(new_scale)
            self._font_regular.configure(size=font_px)
            self._font_bold.configure(size=font_px)
            if self._prev_rows is not None:
                self._prev_rows = None
                self._update_pixels(self._renderer.canvas)

        for (gx, gy), (item_id, _state) in self._glyph_items.items():
            cx, cy = self._cell_center(gx, gy)
            self._canvas.coords(item_id, cx, cy)

    def _cell_center(self, x: int, y: int) -> tuple[float, float]:
        return (
            self._offset_x + (x + 0.5) * self._scale,
            self._offset_y + (y * 2 + 1) * self._scale,
        )

    def _update_pixels(self, scene_canvas: "Canvas") -> None:
        curr_rows = scene_canvas.to_ppm_rows()
        span = dirty_row_span(self._prev_rows, curr_rows)
        if span is None:
            return
        y0, y1 = span
        header = f"P6\n{self._px_w} {y1 - y0}\n255\n".encode("ascii")
        ppm = header + b"".join(curr_rows[y0:y1])
        patch = self._tk.PhotoImage(data=ppm, format="PPM")
        self._dest_photo.tk.call(
            self._dest_photo.name,
            "copy",
            patch.name,
            "-zoom",
            self._scale,
            self._scale,
            "-to",
            0,
            y0 * self._scale,
        )
        self._prev_rows = curr_rows

    def _update_glyphs(self, scene_canvas: "Canvas") -> None:
        desired = {(x, y): (ch, fg, bold) for x, y, ch, fg, bold in scene_canvas.overlay_glyphs()}
        for pos in list(self._glyph_items):
            if pos not in desired:
                item_id, _ = self._glyph_items.pop(pos)
                self._canvas.delete(item_id)

        created = False
        for pos, glyph_state in desired.items():
            existing = self._glyph_items.get(pos)
            if existing is not None and existing[1] == glyph_state:
                continue
            ch, fg, bold = glyph_state
            font = self._font_bold if bold else self._font_regular
            color = rgb_to_hex(fg)
            if existing is None:
                cx, cy = self._cell_center(pos[0], pos[1])
                item_id = self._canvas.create_text(
                    cx,
                    cy,
                    text=ch,
                    fill=color,
                    font=font,
                    anchor="center",
                    tags=("glyph",),
                )
                self._glyph_items[pos] = (item_id, glyph_state)
                created = True
            else:
                item_id = existing[0]
                self._canvas.itemconfigure(item_id, text=ch, fill=color, font=font)
                self._glyph_items[pos] = (item_id, glyph_state)

        if created:
            self._canvas.tag_raise("glyph")

    def render_step(self, now: float) -> None:
        """Advance simulation to `now` and update the Tkinter canvas."""
        t, intro_elapsed = self._state.advance(now)
        scene_canvas = self._renderer.render_frame(t=t, intro_elapsed=intro_elapsed, terminal_size=None)
        self._update_pixels(scene_canvas)
        self._update_glyphs(scene_canvas)

    def _tick(self) -> None:
        if self._closed:
            return
        frame_start = time.monotonic()
        self.render_step(frame_start)
        elapsed = time.monotonic() - frame_start
        delay_ms = max(1, int((self._frame_dt - elapsed) * 1000))
        if not self._closed:
            self._after_id = self._root.after(delay_ms, self._tick)


def run_gui(renderer: "LivingRoomRenderer") -> int:
    """Open a standalone Tkinter window and run the Cozy Christmas Living Room animation."""
    try:
        import tkinter as tk
    except ImportError as exc:
        print(f"Tkinter is not available in this Python installation: {exc}", file=sys.stderr)
        return 1

    _enable_windows_dpi_awareness()
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"Could not open a Tkinter display window: {exc}", file=sys.stderr)
        return 1

    window = LivingRoomWindow(root, renderer)
    window.start()
    return 0
