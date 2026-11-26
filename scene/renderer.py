"""Main scene orchestrator: build-up intro sequence, live animation loop, and keyboard controls."""

from __future__ import annotations

import math
import os
import shutil
import sys
import time

from .canvas import Canvas, CellSnapshot, enable_windows_ansi
from .fireplace import Fireplace
from .furnishings import draw_wall_decorations
from .palette import UI_ACCENT, UI_MUTED, WALL_BG
from .presents import draw_presents
from .room import draw_room_structure, warm_up_room_cache
from .tree import ChristmasTree
from .window import NightWindow


class _KeyReader:
    """Cross-platform non-blocking single-key reader for interactive terminal controls."""

    def __init__(self) -> None:
        self._is_win = os.name == "nt"
        self._old_settings = None
        self._fd: int | None = None

    def __enter__(self) -> "_KeyReader":
        if not self._is_win and sys.stdin.isatty():
            try:
                import termios
                import tty

                self._fd = sys.stdin.fileno()
                self._old_settings = termios.tcgetattr(self._fd)
                tty.setcbreak(self._fd)
            except Exception:
                self._fd = None
        return self

    def __exit__(self, *_: object) -> None:
        if not self._is_win and self._fd is not None and self._old_settings is not None:
            try:
                import termios

                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)
            except Exception:
                pass

    def read_key(self) -> str | None:
        """Return a lowercase key if pressed, otherwise None."""
        if self._is_win:
            try:
                import msvcrt

                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in ("\x00", "\xe0"):
                        if msvcrt.kbhit():
                            msvcrt.getwch()
                        return None
                    return ch.lower()
            except Exception:
                return None
            return None

        if self._fd is None:
            return None
        try:
            import select

            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if ready:
                return sys.stdin.read(1).lower()
        except Exception:
            return None
        return None


class LivingRoomRenderer:
    """Orchestrates the 2D Christmas living room build-up and ambient loop."""

    WIDTH = 116
    HEIGHT = 36

    def __init__(self, fps: float = 30.0, skip_intro: bool = False, intro_speed: float = 1.0) -> None:
        safe_fps = fps if math.isfinite(fps) else 30.0
        safe_speed = intro_speed if math.isfinite(intro_speed) else 1.0
        self.fps = max(5.0, min(60.0, safe_fps))
        self.skip_intro = skip_intro
        self.intro_speed = max(0.25, safe_speed)
        self.lights_on = True

        self.canvas = Canvas(width=self.WIDTH, height=self.HEIGHT, default_bg=WALL_BG)
        self.fireplace = Fireplace(x=3, y=12)
        self.window = NightWindow(x=85, y=4, w=27, h=13)
        self.tree = ChristmasTree(cx=58, top_y=4, bottom_y=24)

    def render_frame(
        self,
        t: float,
        intro_elapsed: float | None = None,
        terminal_size: tuple[int, int] | None = None,
    ) -> Canvas:
        """Render a single frame at simulation time t onto the internal canvas."""
        self.canvas.clear(WALL_BG)

        if intro_elapsed is None:
            room_p = fp_p = win_p = tree_p = decor_p = pres_p = 1.0
            book_p = furn_p = ceil_p = 1.0
            warm_p = electric_p = 1.0
            fire_lit = True
            electric_lit = self.lights_on
            status = "* Cozy Christmas Living Room  │  [L] Lights  [R] Replay Build  [Q] Quit"
        else:
            room_p, fp_p, win_p, book_p, furn_p, tree_p, decor_p, ceil_p, pres_p, warm_p, electric_p, status = (
                self._stage_progress(intro_elapsed)
            )
            fire_lit = warm_p > 0.0
            electric_lit = self.lights_on and electric_p > 0.0

        # Painter's order: walls/floor -> fireplace & window -> wall decor -> tree -> presents -> footer
        draw_room_structure(
            self.canvas,
            t,
            progress=room_p,
            lights_on=electric_lit,
            warm_p=warm_p,
            fire_lit=fire_lit,
            win_p=win_p,
            electric_p=electric_p,
        )
        self.fireplace.draw(self.canvas, t, progress=fp_p, lights_on=fire_lit or electric_lit, warm_p=warm_p)
        self.window.draw(
            self.canvas,
            t,
            progress=win_p,
            lights_on=electric_lit,
            reflect_p=electric_p,
        )
        draw_wall_decorations(
            self.canvas,
            t,
            progress=room_p,
            lights_on=electric_lit,
            ceiling_lights_p=ceil_p,
            bookcase_p=book_p,
            furniture_p=furn_p,
            warm_p=warm_p,
            fire_lit=fire_lit,
            electric_p=electric_p,
        )
        self.tree.draw(
            self.canvas,
            t,
            tree_progress=tree_p,
            decor_progress=decor_p,
            lights_on=electric_lit,
            fire_lit=fire_lit,
            electric_p=electric_p,
        )
        draw_presents(self.canvas, progress=pres_p, lights_on=electric_lit, fire_lit=fire_lit)
        self._draw_footer(status, terminal_size=terminal_size)
        return self.canvas

    def _stage_progress(
        self,
        elapsed: float,
    ) -> tuple[float, float, float, float, float, float, float, float, float, float, float, str]:
        """Compute per-layer [0..1] choreography for the 3-act Twilight-to-Cozy Awakening reveal."""
        s = max(0.0, elapsed) * self.intro_speed
        room_p = min(1.0, s / 1.15)
        win_p = max(0.0, min(1.0, (s - 0.45) / 1.25))
        fp_p = max(0.0, min(1.0, (s - 0.95) / 1.75))
        book_p = max(0.0, min(1.0, (s - 1.20) / 1.05))
        furn_p = max(0.0, min(1.0, (s - 1.50) / 1.20))
        warm_p = max(0.0, min(1.0, (s - 2.15) / 1.05))
        tree_p = max(0.0, min(1.0, (s - 2.65) / 1.35))
        decor_p = max(0.0, min(1.0, (s - 3.90) / 1.35))
        electric_p = max(0.0, min(1.0, (s - 4.15) / 1.15))
        ceil_p = max(0.0, min(1.0, (s - 4.25) / 1.05))
        pres_p = max(0.0, min(1.0, (s - 5.20) / 1.40))

        if s < 1.15:
            msg = "[1/6] Unveiling twilight room, floorboards & Kilim rug... ([Space] Skip)"
        elif s < 2.15:
            msg = "[2/6] Opening frost window & raising brick hearth, bookcase... ([Space] Skip)"
        elif s < 3.15:
            msg = "[3/6] Igniting hearth fire — spreading warm golden glow! ([Space] Skip)"
        elif s < 4.05:
            msg = "[4/6] Growing evergreen pine boughs in amber firelight! ([Space] Skip)"
        elif s < 5.30:
            msg = "[5/6] Awakening tree & ceiling lights, crowning 5-pt star! ([Space] Skip)"
        else:
            msg = "[6/6] Settling wrapped presents beneath the tree!        ([Space] Skip)"
        return room_p, fp_p, win_p, book_p, furn_p, tree_p, decor_p, ceil_p, pres_p, warm_p, electric_p, msg

    def _draw_footer(
        self,
        status: str,
        terminal_size: tuple[int, int] | None = None,
    ) -> None:
        """Render clean status/controls bar on the bottom canvas row."""
        y = self.HEIGHT - 1
        self.canvas.fill_rect(0, y, self.WIDTH, 1, " ", UI_MUTED, bg=(14, 12, 16))
        if terminal_size is not None and (terminal_size[0] < self.WIDTH or terminal_size[1] < self.HEIGHT):
            term_w, term_h = terminal_size
            warn = f"Terminal {term_w}x{term_h} < {self.WIDTH}x{self.HEIGHT} — maximize terminal for full view │ [Q] Quit"
            self.canvas.put_text(2, y, warn[: self.WIDTH - 4], UI_ACCENT, bg=(14, 12, 16), bold=True)
        else:
            self.canvas.put_text(2, y, status[: self.WIDTH - 4], UI_MUTED, bg=(14, 12, 16))

    def warmup(self) -> None:
        """Pre-warm cached room buffers before launching the live intro loop."""
        warm_up_room_cache(self.WIDTH, self.HEIGHT, WALL_BG)

    def run(self) -> None:
        """Start the interactive terminal animation loop until Ctrl+C or Q."""
        enable_windows_ansi()
        if not self.skip_intro:
            self.warmup()
        frame_dt = 1.0 / self.fps
        intro_duration = 6.8 / self.intro_speed

        # Enter alternate screen buffer, hide cursor, and clear once
        sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H")
        sys.stdout.flush()

        start_time = time.monotonic()
        intro_start = start_time
        in_intro = not self.skip_intro
        prev_cells: CellSnapshot | None = None
        prev_geom: tuple[int, int, int, int] | None = None

        try:
            with _KeyReader() as keys:
                while True:
                    now = time.monotonic()
                    t = now - start_time
                    intro_elapsed: float | None = None
                    if in_intro:
                        elapsed = now - intro_start
                        if elapsed >= intro_duration:
                            in_intro = False
                        else:
                            intro_elapsed = elapsed

                    key = keys.read_key()
                    if key in ("q", "\x03"):
                        break
                    if key == "l":
                        self.lights_on = not self.lights_on
                    elif key == "r":
                        intro_start = now
                        in_intro = True
                    elif key in (" ", "\r", "\n") and in_intro:
                        in_intro = False

                    term_w, term_h = shutil.get_terminal_size((self.WIDTH, self.HEIGHT))
                    self.render_frame(t=t, intro_elapsed=intro_elapsed, terminal_size=(term_w, term_h))
                    clipped = term_w < self.WIDTH or term_h < self.HEIGHT
                    offset_x = 0 if clipped else max(0, (term_w - self.WIDTH) // 2)
                    offset_y = 0 if clipped else max(0, (term_h - self.HEIGHT) // 2)
                    max_w = term_w if clipped else self.WIDTH
                    max_h = term_h if clipped else self.HEIGHT

                    geom = (max_w, max_h, offset_x, offset_y)
                    if geom != prev_geom:
                        prev_cells = None
                        prev_geom = geom

                    payload, prev_cells = self.canvas.to_ansi_diff(
                        prev_cells,
                        offset_x=offset_x,
                        offset_y=offset_y,
                        max_w=max_w,
                        max_h=max_h,
                        skip_bottom_right=clipped,
                    )
                    sys.stdout.write(payload)
                    sys.stdout.flush()

                    sleep_for = frame_dt - (time.monotonic() - now)
                    if sleep_for > 0:
                        time.sleep(sleep_for)
        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
            sys.stdout.flush()
