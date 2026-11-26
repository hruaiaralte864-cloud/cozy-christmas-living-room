"""24-bit TrueColor 2D character & half-block sub-pixel buffer for flicker-free ANSI rendering."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from itertools import chain

from .palette import RGB, WALL_BG

CellSnapshot = list[list[tuple[str, RGB, RGB | None, bool]]]

_Q16_LUT: tuple[int, ...] = tuple(255 if c >= 248 else ((c + 8) & 0xF0) for c in range(256))


def enable_windows_ansi() -> None:
    """Enable ANSI/VT100 escape processing and UTF-8 output on Windows consoles."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            enable_vt = 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.SetConsoleMode(handle, mode.value | enable_vt)
    except Exception:
        pass


@dataclass(slots=True)
class Cell:
    """Single terminal character cell with foreground/background TrueColor."""

    char: str = " "
    fg: RGB = (220, 220, 220)
    bg: RGB | None = None
    bold: bool = False


class Canvas:
    """Fixed-resolution 2D cell buffer with integrated 2x-vertical half-block sub-pixel support."""

    _PLAIN_RAMP = " .:-=+*#%@"

    def __init__(self, width: int = 116, height: int = 36, default_bg: RGB = WALL_BG) -> None:
        self.width = width
        self.height = height
        self.px_height = height * 2
        self.default_bg = default_bg
        self._grid: list[list[Cell]] = [
            [Cell(bg=default_bg) for _ in range(width)] for _ in range(height)
        ]
        self._top_px: list[list[RGB]] = [
            [default_bg for _ in range(width)] for _ in range(height)
        ]
        self._bot_px: list[list[RGB]] = [
            [default_bg for _ in range(width)] for _ in range(height)
        ]

    def clear(self, bg: RGB | None = None) -> None:
        """Reset all character cells and sub-pixels to the background color."""
        fill_bg = self.default_bg if bg is None else bg
        for y in range(self.height):
            row = self._grid[y]
            top_row = self._top_px[y]
            bot_row = self._bot_px[y]
            for x in range(self.width):
                cell = row[x]
                cell.char = " "
                cell.fg = (220, 220, 220)
                cell.bg = fill_bg
                cell.bold = False
                top_row[x] = fill_bg
                bot_row[x] = fill_bg

    def load_subpixel_frame(self, top_rows: list[list[RGB]], bot_rows: list[list[RGB]]) -> None:
        """Fast-load precomputed top/bottom sub-pixel rows and sync the character grid."""
        for y in range(min(self.height, len(top_rows))):
            src_top = top_rows[y]
            src_bot = bot_rows[y]
            dst_top = self._top_px[y]
            dst_bot = self._bot_px[y]
            row = self._grid[y]
            for x in range(min(self.width, len(src_top))):
                top = src_top[x]
                bot = src_bot[x]
                dst_top[x] = top
                dst_bot[x] = bot
                cell = row[x]
                cell.bold = False
                if top == bot:
                    cell.char = " "
                    cell.fg = top
                    cell.bg = top
                else:
                    cell.char = "▀"
                    cell.fg = top
                    cell.bg = bot

    def _sync_pixel_cell(self, x: int, y: int) -> None:
        """Sync character cell (x, y) from its top and bottom sub-pixel RGB values."""
        top = self._top_px[y][x]
        bot = self._bot_px[y][x]
        cell = self._grid[y][x]
        cell.bold = False
        if top == bot:
            cell.char = " "
            cell.fg = top
            cell.bg = top
        else:
            cell.char = "▀"
            cell.fg = top
            cell.bg = bot

    def set_px(self, x: int, py: int, color: RGB) -> None:
        """Set a single sub-pixel in the (width x 2*height) pixel grid."""
        if 0 <= x < self.width and 0 <= py < self.px_height:
            y = py >> 1
            if py & 1:
                self._bot_px[y][x] = color
            else:
                self._top_px[y][x] = color
            self._sync_pixel_cell(x, y)

    def get_px(self, x: int, py: int) -> RGB:
        """Return the sub-pixel RGB at (x, py) or default_bg if out of bounds."""
        if 0 <= x < self.width and 0 <= py < self.px_height:
            y = py >> 1
            return self._bot_px[y][x] if (py & 1) else self._top_px[y][x]
        return self.default_bg

    def blend_px(self, x: int, py: int, color: RGB, alpha: float) -> None:
        """Alpha-blend color onto sub-pixel (x, py) with alpha in [0, 1]."""
        if alpha <= 0.0 or not (0 <= x < self.width and 0 <= py < self.px_height):
            return
        if alpha >= 1.0:
            self.set_px(x, py, color)
            return
        y = py >> 1
        base = self._bot_px[y][x] if (py & 1) else self._top_px[y][x]
        blended: RGB = (
            int(base[0] + (color[0] - base[0]) * alpha),
            int(base[1] + (color[1] - base[1]) * alpha),
            int(base[2] + (color[2] - base[2]) * alpha),
        )
        if py & 1:
            self._bot_px[y][x] = blended
        else:
            self._top_px[y][x] = blended
        self._sync_pixel_cell(x, y)

    def put(
        self,
        x: int,
        y: int,
        char: str,
        fg: RGB,
        bg: RGB | None = None,
        bold: bool = False,
    ) -> None:
        """Draw a single character if (x, y) is inside canvas bounds."""
        if 0 <= x < self.width and 0 <= y < self.height and char:
            cell = self._grid[y][x]
            cell.char = char[0]
            cell.fg = fg
            if bg is not None:
                cell.bg = bg
                self._top_px[y][x] = bg
                self._bot_px[y][x] = bg
            elif cell.char != "▀":
                t = self._top_px[y][x]
                b = self._bot_px[y][x]
                cell.bg = ((t[0] + b[0]) >> 1, (t[1] + b[1]) >> 1, (t[2] + b[2]) >> 1)
            cell.bold = bold

    def get(self, x: int, y: int) -> Cell | None:
        """Return the cell at (x, y) or None if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._grid[y][x]
        return None

    def put_text(
        self,
        x: int,
        y: int,
        text: str,
        fg: RGB,
        bg: RGB | None = None,
        bold: bool = False,
        skip_spaces: bool = False,
    ) -> None:
        """Write a string horizontally starting at (x, y)."""
        for idx, ch in enumerate(text):
            if skip_spaces and ch == " ":
                continue
            self.put(x + idx, y, ch, fg, bg=bg, bold=bold)

    def fill_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        char: str = " ",
        fg: RGB = (200, 200, 200),
        bg: RGB | None = None,
        bold: bool = False,
    ) -> None:
        """Fill a rectangular region on the canvas."""
        for row in range(y, y + h):
            for col in range(x, x + w):
                self.put(col, row, char, fg, bg=bg, bold=bold)

    def snapshot(self, max_w: int | None = None, max_h: int | None = None) -> CellSnapshot:
        """Capture a snapshot keeping full 24-bit space quads and bounded 16-step half-blocks."""
        w = self.width if max_w is None else max(1, min(self.width, max_w))
        h = self.height if max_h is None else max(1, min(self.height, max_h))
        q16 = _Q16_LUT
        rows: CellSnapshot = []
        for y in range(h):
            row_out: list[tuple[str, RGB, RGB | None, bool]] = []
            for cell in self._grid[y][:w]:
                fg = cell.fg
                cbg = cell.bg
                if cell.char == "▀" and cbg is not None:
                    fr, fg_c, fb = fg
                    br, bg_c, bb = cbg
                    if (
                        abs(fr - br) <= 14
                        and abs(fg_c - bg_c) <= 14
                        and abs(fb - bb) <= 14
                    ):
                        # Collapse subtle sub-pixel differences to full 24-bit space quads (0 atlas slots)
                        avg: RGB = ((fr + br) >> 1, (fg_c + bg_c) >> 1, (fb + bb) >> 1)
                        row_out.append((" ", avg, avg, False))
                    else:
                        fg16: RGB = (q16[fr], q16[fg_c], q16[fb])
                        bg16: RGB = (q16[br], q16[bg_c], q16[bb])
                        if fg16 == bg16:
                            row_out.append((" ", fg16, bg16, False))
                        else:
                            row_out.append(("▀", fg16, bg16, False))
                else:
                    row_out.append((cell.char, fg, cbg, cell.bold))
            rows.append(row_out)
        return rows

    def to_ansi_diff(
        self,
        prev: CellSnapshot | None,
        offset_x: int = 0,
        offset_y: int = 0,
        max_w: int | None = None,
        max_h: int | None = None,
        skip_bottom_right: bool = False,
    ) -> tuple[str, CellSnapshot]:
        """Serialize only changed cells using explicit cursor positioning & sync-output framing."""
        clip_w = self.width if max_w is None else max(1, min(self.width, max_w))
        clip_h = self.height if max_h is None else max(1, min(self.height, max_h))
        curr = self.snapshot(max_w=clip_w, max_h=clip_h)
        full_redraw = (
            prev is None
            or len(prev) != clip_h
            or (clip_h > 0 and len(prev[0]) != clip_w)
        )

        # Wrap frame in DEC Synchronized Output (?2026) so terminals never tear mid-frame
        out: list[str] = ["\x1b[?2026h"]
        if full_redraw:
            out.append("\x1b[0m\x1b[2J")

        prev_fg: RGB | None = None
        prev_bg: RGB | None = None
        prev_bold: bool | None = None

        for y in range(clip_h):
            row_curr = curr[y]
            row_prev = None if full_redraw else prev[y]
            term_row = offset_y + y + 1
            cursor_x = -1
            row_limit = clip_w - 1 if (skip_bottom_right and y == clip_h - 1) else clip_w

            for x in range(row_limit):
                state = row_curr[x]
                if row_prev is not None and state == row_prev[x]:
                    continue

                if cursor_x != x:
                    out.append(f"\x1b[{term_row};{offset_x + x + 1}H")

                ch, fg, bg, bold = state
                if bold != prev_bold:
                    out.append("\x1b[1m" if bold else "\x1b[22m")
                    prev_bold = bold
                if fg != prev_fg:
                    out.append(f"\x1b[38;2;{fg[0]};{fg[1]};{fg[2]}m")
                    prev_fg = fg
                if bg != prev_bg:
                    if bg is None:
                        out.append("\x1b[49m")
                    else:
                        out.append(f"\x1b[48;2;{bg[0]};{bg[1]};{bg[2]}m")
                    prev_bg = bg

                out.append(ch)
                cursor_x = x + 1

        out.append("\x1b[0m\x1b[?2026l")
        return "".join(out), curr

    def _plain_char(self, x: int, y: int, cell: Cell) -> str:
        """Convert sub-pixel half-block cells into a readable ASCII luminance glyph for --plain."""
        if cell.char not in ("▀", " "):
            return cell.char
        if cell.char == " " and (cell.bg is None or cell.bg == self.default_bg):
            return " "
        top = self._top_px[y][x]
        bot = self._bot_px[y][x]
        lum = (
            0.299 * (top[0] + bot[0])
            + 0.587 * (top[1] + bot[1])
            + 0.114 * (top[2] + bot[2])
        ) / 510.0
        base_lum = (
            0.299 * self.default_bg[0] + 0.587 * self.default_bg[1] + 0.114 * self.default_bg[2]
        ) / 255.0
        if cell.char == " " and abs(lum - base_lum) < 0.045:
            return " "
        idx = max(0, min(len(self._PLAIN_RAMP) - 1, int(lum * (len(self._PLAIN_RAMP) - 1))))
        return self._PLAIN_RAMP[idx]

    def to_ansi(self, offset_x: int = 0, offset_y: int = 0, plain: bool = False) -> str:
        """Serialize the entire buffer into a single ANSI string for static/full output."""
        if plain:
            return "\n".join(
                "".join(self._plain_char(x, y, cell) for x, cell in enumerate(row))
                for y, row in enumerate(self._grid)
            )

        out: list[str] = ["\x1b[H"]
        if offset_y > 0:
            out.append("\n" * offset_y)

        pad_left = " " * max(0, offset_x)
        prev_fg: RGB | None = None
        prev_bg: RGB | None = None
        prev_bold: bool | None = None

        for y, row in enumerate(self._grid):
            if pad_left:
                out.append("\x1b[0m" + pad_left)
                prev_fg = None
                prev_bg = None
                prev_bold = None
            for cell in row:
                if cell.bold != prev_bold:
                    out.append("\x1b[1m" if cell.bold else "\x1b[22m")
                    prev_bold = cell.bold
                if cell.fg != prev_fg:
                    r, g, b = cell.fg
                    out.append(f"\x1b[38;2;{r};{g};{b}m")
                    prev_fg = cell.fg
                if cell.bg != prev_bg:
                    if cell.bg is None:
                        out.append("\x1b[49m")
                    else:
                        r, g, b = cell.bg
                        out.append(f"\x1b[48;2;{r};{g};{b}m")
                    prev_bg = cell.bg
                out.append(cell.char)
            if y < self.height - 1:
                out.append("\x1b[0m\n")
                prev_fg = None
                prev_bg = None
                prev_bold = None

        out.append("\x1b[0m")
        return "".join(out)

    def to_ppm_rows(self) -> list[bytes]:
        """Serialize the 2x-vertical sub-pixel buffer into raw RGB byte rows."""
        rows: list[bytes] = []
        for y in range(self.height):
            for px_row in (self._top_px[y], self._bot_px[y]):
                rows.append(bytes(chain.from_iterable(px_row)))
        return rows

    def to_ppm_bytes(self) -> bytes:
        """Serialize the full sub-pixel buffer as a binary P6 PPM image."""
        header = f"P6\n{self.width} {self.px_height}\n255\n".encode("ascii")
        return header + b"".join(self.to_ppm_rows())

    def overlay_glyphs(self) -> list[tuple[int, int, str, RGB, bool]]:
        """Return (x, y, char, fg, bold) tuples for non-block glyph cells."""
        glyphs: list[tuple[int, int, str, RGB, bool]] = []
        for y, row in enumerate(self._grid):
            for x, cell in enumerate(row):
                if cell.char not in (" ", "▀"):
                    glyphs.append((x, y, cell.char, cell.fg, cell.bold))
        return glyphs
