"""Brick fireplace renderer: keystone arch, crossed logs, curling flames, and mantel props."""

from __future__ import annotations

import math
import random

from .canvas import Canvas
from .palette import (
    BRICK_DARK,
    BRICK_LIGHT,
    BRICK_MID,
    BRICK_MORTAR,
    BRICK_WARM_GLOW,
    CUFF_WHITE,
    FIRE_PALETTE,
    FLOOR_WOOD_LIGHT,
    HEARTH_BG,
    LOG_WOOD,
    MANTEL_BG,
    MANTEL_WOOD,
    PINE_DARK,
    PINE_LIGHT,
    PINE_MID,
    RGB,
    SHADOW_PLUM,
    STAR_BRIGHT,
    STOCKING_GREEN,
    STOCKING_RED,
    TINSEL_GOLD,
    hash01,
    lerp_rgb,
    scale_rgb,
)
from .room import is_warm_lit


def _draw_sprite_clipped(
    canvas: Canvas,
    x0: int,
    py0: int,
    sprite: list[str] | tuple[str, ...],
    palette: dict[str, RGB],
    min_py: int = 0,
) -> None:
    """Blit an indexed pixel sprite clipped safely at min_py for bottom-up intro reveals."""
    for dy, row in enumerate(sprite):
        py = py0 + dy
        if py < min_py:
            continue
        for dx, ch in enumerate(row):
            if ch != ".":
                canvas.set_px(x0 + dx, py, palette[ch])


def _draw_sprite_shadow_clipped(
    canvas: Canvas,
    x0: int,
    py0: int,
    sprite: list[str] | tuple[str, ...],
    alpha: float,
    min_py: int = 0,
) -> None:
    """Project a 1-px (+1, +1) silhouette drop shadow clipped safely at min_py."""
    rows = len(sprite)
    cols = len(sprite[0])
    for dy, row in enumerate(sprite):
        if py0 + dy + 1 < min_py:
            continue
        for dx, ch in enumerate(row):
            if ch == ".":
                continue
            sx, sy = dx + 1, dy + 1
            if sx >= cols or sy >= rows or sprite[sy][sx] == ".":
                canvas.blend_px(x0 + sx, py0 + sy, SHADOW_PLUM, alpha)


class Fireplace:
    """Animated brick hearth with recessed firebox, crossed logs, flames, and mantel props."""

    _WARM_ATTEN = 0.94

    def __init__(self, x: int = 3, y: int = 12, seed: int = 42) -> None:
        self.x = x
        self.y = y
        self.rng = random.Random(seed)
        self.fire_w = 12
        self.fire_px_h = 16

        # Rising sparks: [x, py, speed, phase, amp]
        self.embers: list[list[float]] = [
            [
                self.rng.uniform(2.0, self.fire_w - 3.0),
                self.rng.uniform(1.0, self.fire_px_h - 4.0),
                self.rng.uniform(0.18, 0.38),
                self.rng.uniform(0.0, math.tau),
                self.rng.uniform(0.35, 0.85),
            ]
            for _ in range(10)
        ]

    def draw(
        self,
        canvas: Canvas,
        t: float,
        progress: float = 1.0,
        lights_on: bool = True,
        warm_p: float = 1.0,
    ) -> None:
        """Render chimney, keystone arch, firebox, mantel props, stockings, and rising fire."""
        if progress <= 0.02:
            return

        x0, y0 = self.x, self.y
        mantel_py = y0 * 2  # py = 24
        e_brick = 1.0 - (1.0 - min(1.0, progress / 0.54)) ** 2
        min_py = 2 if progress >= 0.54 else max(2, int(round(52.0 - e_brick * 50.0)))
        brick_warm = 1.0 if progress >= 1.0 else max(0.0, min(1.0, (progress - 0.56) / 0.24))
        wp = 0.0 if (not lights_on or brick_warm <= 0.0) else max(0.0, min(1.0, warm_p * brick_warm))
        fx0, fx1 = x0 + 6, x0 + 19
        fy0, fy1 = mantel_py + 8, mantel_py + 25

        self._draw_masonry_shell(canvas, x0, mantel_py, fx0, fx1, fy0, fy1, min_py, lights_on, wp)
        self._draw_mantel_and_hearth(canvas, x0, mantel_py, t, lights_on, min_py=min_py, warm_p=wp)

        sock_p = 1.0 if progress >= 0.58 else max(0.0, min(1.0, (progress - 0.34) / 0.24))
        if sock_p > 0.01:
            sock_min_py = 0 if sock_p >= 1.0 else 38 - int(round(11.0 * (1.0 - (1.0 - sock_p) ** 2)))
            self._draw_stocking(canvas, x0 + 1, mantel_py + 3, STOCKING_RED, True, lights_on, wp, sock_min_py)
            self._draw_stocking(canvas, x0 + 20, mantel_py + 3, STOCKING_GREEN, False, lights_on, wp, sock_min_py)

        prop_p = 1.0 if progress >= 0.68 else max(0.0, min(1.0, (progress - 0.44) / 0.24))
        if prop_p > 0.01:
            prop_min_py = 0 if prop_p >= 1.0 else 27 - int(round(21.0 * (1.0 - (1.0 - prop_p) ** 2)))
            self._draw_mantel_props(canvas, x0, mantel_py, lights_on=lights_on, warm_p=wp, min_py=prop_min_py)

        if progress >= 0.30:
            log_p = 1.0 if progress >= 0.55 else (progress - 0.30) / 0.25
            fire_min_py = 0 if log_p >= 1.0 else fy1 + 2 - int(round(6.0 * (1.0 - (1.0 - log_p) ** 2)))
            ember_p = 1.0 if progress >= 0.72 else max(0.0, min(1.0, (progress - 0.56) / 0.16))
            fire_p = 0.0 if progress < 0.66 else max(0.0, min(1.0, (progress - 0.66) / 0.34))
            self._draw_fire(canvas, fx0 + 1, fy0 + 1, t, lights_on=lights_on, fire_p=fire_p, min_py=fire_min_py, ember_p=ember_p)

    def _draw_masonry_shell(
        self,
        canvas: Canvas,
        x0: int,
        mantel_py: int,
        fx0: int,
        fx1: int,
        fy0: int,
        fy1: int,
        min_py: int,
        lights_on: bool,
        wp: float,
    ) -> None:
        """Render chimney breast, brick piers, and recessed keystone firebox."""
        if min_py <= mantel_py - 1:
            self._draw_brick_region(
                canvas, x0 + 5, x0 + 20, max(2, min_py), mantel_py - 1,
                lights_on=lights_on, warm_p=wp, hearth_cx=x0 + 13, hearth_py=mantel_py + 4, dim=0.78,
            )
        if min_py <= mantel_py + 25:
            self._draw_brick_region(
                canvas, x0 + 1, x0 + 24, max(mantel_py + 2, min_py), mantel_py + 25,
                lights_on=lights_on, warm_p=wp, hearth_cx=x0 + 13, hearth_py=mantel_py + 18, dim=1.0,
            )
        if min_py <= fy1:
            self._draw_firebox_masonry(canvas, fx0, fx1, fy0, fy1, lights_on, min_py=min_py, warm_p=wp)

    def _draw_brick_region(
        self,
        canvas: Canvas,
        x_start: int,
        x_end: int,
        py_start: int,
        py_end: int,
        lights_on: bool,
        hearth_cx: int,
        hearth_py: int,
        dim: float,
        warm_p: float = 1.0,
    ) -> None:
        """Render staggered running-bond masonry with subtle brick bevels and warm glow."""
        for py in range(py_start, py_end + 1):
            course = (py - py_start) // 3
            in_course = (py - py_start) % 3
            stagger = (course % 2) * 2
            is_h_mortar = in_course == 2

            for x in range(x_start, x_end + 1):
                brick_id = (x + stagger) // 4
                is_v_mortar = (x + stagger) % 4 == 0
                if is_h_mortar or is_v_mortar:
                    # Soften mortar lines on the upper chimney (above hearth crown) so wreath & Drummer Boy pop
                    col = lerp_rgb(BRICK_MORTAR, BRICK_DARK, 0.42) if py < 24 else BRICK_MORTAR
                    col = scale_rgb(col, 1.0 if lights_on else 0.78)
                else:
                    tone = (brick_id * 7 + course * 13) % 6
                    base = BRICK_LIGHT if tone == 0 else (BRICK_DARK if tone >= 4 else BRICK_MID)
                    dist = math.hypot((x - hearth_cx) * 0.55, (py - hearth_py) * 0.65)
                    px_lit = is_warm_lit(x, py, lights_on, warm_p)
                    warm = max(0.0, 1.0 - dist / 14.0) * (0.52 if px_lit else 0.10) * self._WARM_ATTEN
                    col = lerp_rgb(scale_rgb(base, dim), BRICK_WARM_GLOW, warm)
                    if in_course == 0:
                        col = scale_rgb(col, 1.08)
                # Subtle edge shadow along outer chimney/surround sides
                if x in (x_start, x_end):
                    col = lerp_rgb(col, SHADOW_PLUM, 0.25)
                canvas.set_px(x, py, col)

    def _draw_firebox_masonry(
        self,
        canvas: Canvas,
        fx0: int,
        fx1: int,
        fy0: int,
        fy1: int,
        lights_on: bool,
        min_py: int = 0,
        warm_p: float = 1.0,
    ) -> None:
        """Render keystone brick arch, soot darkening, inner brick jambs, and back firebrick wall."""
        if min_py <= fy0 - 1:
            # Subtle soot weathering above the arch lintel
            for py in range(max(min_py, fy0 - 4), fy0 - 1):
                for x in range(fx0 + 2, fx1 - 1):
                    soot = max(0.0, 1.0 - abs(x - (fx0 + fx1) / 2.0) / 5.5) * 0.32
                    canvas.blend_px(x, py, SHADOW_PLUM, soot)

            # Curved voussoir brick arch + lighter central keystone (x = 15..16)
            for x in range(fx0, fx1 + 1):
                is_keystone = x in (fx0 + 6, fx0 + 7)
                is_corner = x in (fx0, fx1)
                arch_base = (146, 132, 122) if is_keystone else BRICK_LIGHT
                arch_lit = is_warm_lit(x, fy0 - 1, lights_on, warm_p)
                warm = (0.38 if arch_lit else 0.08) * self._WARM_ATTEN
                arch_col = lerp_rgb(arch_base, BRICK_WARM_GLOW, warm)
                if is_corner:
                    canvas.set_px(x, fy0 - 1, scale_rgb(BRICK_DARK, 0.9))
                    canvas.set_px(x, fy0, scale_rgb(BRICK_MORTAR, 1.1))
                elif is_keystone:
                    if min_py <= fy0 - 3:
                        canvas.set_px(x, fy0 - 3, scale_rgb(arch_col, 1.05))
                    if min_py <= fy0 - 2:
                        canvas.set_px(x, fy0 - 2, arch_col)
                    canvas.set_px(x, fy0 - 1, scale_rgb(arch_col, 0.85))
                else:
                    alt = 0.90 if (x % 2 == 0) else 1.04
                    if min_py <= fy0 - 2:
                        canvas.set_px(x, fy0 - 2, scale_rgb(arch_col, 0.88 * alt))
                    canvas.set_px(x, fy0 - 1, scale_rgb(arch_col, alt))

        # Recessed back firebrick wall + glowing angled side jambs
        fire_cx = (fx0 + fx1) / 2.0
        fire_cy = fy1 - 5.0
        for py in range(max(fy0, min_py), fy1 + 1):
            course = (py - fy0) // 2
            is_mortar_row = (py - fy0) % 2 == 1
            for x in range(fx0, fx1 + 1):
                px_lit = is_warm_lit(x, py, lights_on, warm_p)
                if x in (fx0, fx1):
                    # Angled side jambs catching orange rim bounce near lower fire
                    jamb_warm = max(0.0, 1.0 - max(0, (fy1 - 4 - py)) / 10.0)
                    col = lerp_rgb(
                        BRICK_MORTAR, BRICK_WARM_GLOW, jamb_warm * (0.58 if px_lit else 0.12) * self._WARM_ATTEN
                    )
                    canvas.set_px(x, py, col)
                elif py == fy0 and x in (fx0 + 1, fx1 - 1):
                    # Rounded upper arch corners inside firebox
                    canvas.set_px(x, py, BRICK_MORTAR)
                else:
                    # Back firebrick wall illuminated behind flames, darker soot at top
                    is_v_mortar = (x + (course % 2) * 2) % 4 == 0
                    base_back = HEARTH_BG if (is_mortar_row or is_v_mortar) else (44, 20, 20)
                    dist = math.hypot((x - fire_cx) * 0.65, (py - fire_cy) * 0.72)
                    glow = max(0.0, 1.0 - dist / 8.5) * (0.62 if px_lit else 0.10) * self._WARM_ATTEN
                    col = lerp_rgb(base_back, FIRE_PALETTE[1], glow)
                    if py <= fy0 + 2:
                        col = lerp_rgb(col, SHADOW_PLUM, 0.45)
                    canvas.set_px(x, py, col)

    def _draw_mantel_and_hearth(
        self,
        canvas: Canvas,
        x0: int,
        mantel_py: int,
        t: float,
        lights_on: bool,
        min_py: int = 0,
        warm_p: float = 1.0,
    ) -> None:
        """Render walnut mantelpiece, slate hearth apron, spark fender, and tool stand."""
        self._draw_mantel_shelf(canvas, x0, mantel_py, min_py)
        self._draw_hearth_apron(canvas, x0, mantel_py, lights_on, min_py, warm_p)
        self._draw_fender_and_tools(canvas, x0, mantel_py, t, lights_on, min_py, warm_p)

    def _draw_mantel_shelf(self, canvas: Canvas, x0: int, mantel_py: int, min_py: int) -> None:
        """Render walnut mantelpiece shelf (py = 24..26) and carved corbels (py = 27..29)."""
        if min_py <= mantel_py + 2:
            for x in range(x0, x0 + 26):
                if min_py <= mantel_py:
                    canvas.set_px(x, mantel_py, scale_rgb(MANTEL_WOOD, 1.12))
                if min_py <= mantel_py + 1:
                    canvas.set_px(x, mantel_py + 1, MANTEL_WOOD)
                if x0 + 1 <= x <= x0 + 24:
                    canvas.set_px(x, mantel_py + 2, scale_rgb(MANTEL_BG, 0.78))

        if min_py <= mantel_py + 5:
            for bx in (x0 + 2, x0 + 22):
                if min_py <= mantel_py + 3:
                    canvas.set_px(bx, mantel_py + 3, MANTEL_WOOD)
                    canvas.set_px(bx + 1, mantel_py + 3, scale_rgb(MANTEL_WOOD, 0.82))
                if min_py <= mantel_py + 4:
                    canvas.set_px(bx, mantel_py + 4, scale_rgb(MANTEL_WOOD, 0.82))
                    canvas.blend_px(bx + 1, mantel_py + 4, SHADOW_PLUM, 0.35)
                canvas.set_px(bx, mantel_py + 5, scale_rgb(MANTEL_BG, 0.85))

    def _draw_hearth_apron(
        self,
        canvas: Canvas,
        x0: int,
        mantel_py: int,
        lights_on: bool,
        min_py: int,
        warm_p: float,
    ) -> None:
        """Render flagged slate hearth stones (x = 2..27, py = 50..51) and floor shadow."""
        slate_a, slate_b = (110, 92, 86), (94, 78, 76)
        slate_bevel, slate_joint = (68, 52, 52), (50, 38, 42)

        for x in range(x0 - 1, x0 + 25):
            hearth_lit = is_warm_lit(x, mantel_py + 26, lights_on, warm_p)
            amber_bounce = FIRE_PALETTE[2] if hearth_lit else scale_rgb(BRICK_WARM_GLOW, 0.25)
            warm = max(0.0, 1.0 - abs(x - (x0 + 12.5)) / 8.5) * (0.44 if hearth_lit else 0.08) * self._WARM_ATTEN
            tile_idx = 0 if x < x0 + 3 else (1 if x < x0 + 10 else (2 if x < x0 + 18 else 3))

            base_top = slate_a if tile_idx % 2 == 0 else slate_b
            top_c = slate_joint if (x - x0) in (3, 10, 18) else lerp_rgb(base_top, amber_bounce, warm)
            lip_c = slate_joint if (x - x0) in (6, 14, 21) else lerp_rgb(slate_bevel, BRICK_WARM_GLOW, warm * 0.65)
            if x in (x0 - 1, x0 + 24):
                top_c = scale_rgb(top_c, 0.85)
                lip_c = slate_joint

            if min_py <= mantel_py + 26:
                canvas.set_px(x, mantel_py + 26, top_c)
            if min_py <= mantel_py + 27:
                canvas.set_px(x, mantel_py + 27, lip_c)
            if min_py <= mantel_py + 28:
                canvas.blend_px(x, mantel_py + 28, SHADOW_PLUM, 0.55)

    def _draw_fender_and_tools(
        self,
        canvas: Canvas,
        x0: int,
        mantel_py: int,
        t: float,
        lights_on: bool,
        min_py: int,
        warm_p: float,
    ) -> None:
        """Render brass-knobbed spark fender and wrought-iron fireplace tool stand."""
        iron, iron_hi = (44, 42, 52), (88, 86, 98)
        fire_spark = round((0.50 + 0.50 * math.sin(t * 4.2 + 0.5)) * 2.0) / 2.0
        brass_spark = lerp_rgb(TINSEL_GOLD, STAR_BRIGHT, 0.45 * fire_spark)

        if min_py <= mantel_py + 25:
            for fx in range(x0 + 5, x0 + 21):
                brass_knob = brass_spark if is_warm_lit(fx, mantel_py + 24, lights_on, warm_p) else scale_rgb(TINSEL_GOLD, 0.48)
                if fx in (x0 + 5, x0 + 20):
                    if min_py <= mantel_py + 24:
                        canvas.set_px(fx, mantel_py + 24, brass_knob)
                    canvas.set_px(fx, mantel_py + 25, iron_hi)
                else:
                    canvas.set_px(fx, mantel_py + 25, (70, 62, 68) if fx % 3 == 0 else iron)

        tx = x0 + 25
        stand_brass = (
            lerp_rgb(TINSEL_GOLD, STAR_BRIGHT, 0.36 * fire_spark)
            if is_warm_lit(tx, mantel_py + 16, lights_on, warm_p)
            else scale_rgb(TINSEL_GOLD, 0.48)
        )
        if min_py <= mantel_py + 27:
            canvas.set_px(tx, mantel_py + 27, iron)
            canvas.set_px(tx + 1, mantel_py + 27, iron_hi)
            canvas.blend_px(tx, mantel_py + 28, SHADOW_PLUM, 0.50)
            canvas.blend_px(tx + 1, mantel_py + 28, SHADOW_PLUM, 0.50)
        for py in range(max(mantel_py + 15, min_py), mantel_py + 27):
            canvas.set_px(tx, py, iron_hi if py == mantel_py + 15 else iron)
            if py >= mantel_py + 18:
                canvas.set_px(tx + 1, py, scale_rgb(iron, 0.85))
        if min_py <= mantel_py + 15:
            canvas.set_px(tx, mantel_py + 15, stand_brass)
        if min_py <= mantel_py + 17:
            canvas.set_px(tx + 1, mantel_py + 17, stand_brass)

    def _draw_mantel_props(
        self,
        canvas: Canvas,
        x0: int,
        mantel_py: int,
        lights_on: bool,
        warm_p: float = 1.0,
        min_py: int = 0,
    ) -> None:
        """Render hero chimney wreath, pinecone garland, Little Drummer Boy, and snowglobe."""
        self._draw_chimney_wreath(
            canvas, x0 + 7, mantel_py - 18,
            lights_on=is_warm_lit(x0 + 13, mantel_py - 11, lights_on, warm_p),
            min_py=min_py,
        )
        self._draw_mantel_garland(
            canvas, x0, mantel_py, lights_on=lights_on, warm_p=warm_p, min_py=min_py
        )
        self._draw_mantel_drummer_boy(
            canvas, x0 + 1, mantel_py - 14,
            lights_on=is_warm_lit(x0 + 4, mantel_py - 7, lights_on, warm_p),
            min_py=min_py,
        )
        self._draw_mantel_snowglobe(
            canvas, x0 + 19, mantel_py - 6,
            lights_on=is_warm_lit(x0 + 21, mantel_py - 3, lights_on, warm_p),
            min_py=min_py,
        )

    def _draw_chimney_wreath(
        self,
        canvas: Canvas,
        wx: int,
        wy: int,
        lights_on: bool,
        min_py: int = 0,
    ) -> None:
        """Render a sculpted evergreen chimney wreath with berries, brass accents, and velvet bow."""
        dim = 1.0 if lights_on else 0.50
        palette = {
            "L": scale_rgb(PINE_LIGHT, dim),
            "M": scale_rgb(PINE_MID, dim),
            "D": scale_rgb(PINE_DARK, dim),
            "S": (18, 38, 30) if lights_on else (12, 24, 22),
            "W": lerp_rgb(PINE_MID, FIRE_PALETTE[2], 0.24) if lights_on else scale_rgb(PINE_DARK, 0.55),
            "R": STOCKING_RED if lights_on else scale_rgb(STOCKING_RED, 0.52),
            "H": lerp_rgb(STOCKING_RED, STAR_BRIGHT, 0.40) if lights_on else scale_rgb(STOCKING_RED, 0.62),
            "V": scale_rgb(STOCKING_RED, 0.56 if lights_on else 0.34),
            "G": TINSEL_GOLD if lights_on else scale_rgb(TINSEL_GOLD, 0.48),
        }
        sprite = [
            "....LMLM....",
            "..LMLMGRHM..",
            ".LMDSMDDMML.",
            "LMRHM..DMDML",
            "MDML....LMDM",
            "LMGD....MDMD",
            "MDMS....MRHD",
            "LMDW....WSMD",
            ".MDWVRRVWMD.",
            ".LWHRVVRHWL.",
            "..RHRVVRHR..",
            "...VRVVRV...",
            "...RV..VR...",
            "..RV....VR..",
        ]
        # Pass 1: Soft directional brick drop shadow inside donut hole & lower-right edge
        _draw_sprite_shadow_clipped(canvas, wx, wy, sprite, 0.55 if lights_on else 0.42, min_py=min_py)

        # Pass 2: Layered pine boughs, holly berries, and crimson velvet bow
        _draw_sprite_clipped(canvas, wx, wy, sprite, palette, min_py=min_py)

    def _draw_mantel_drummer_boy(
        self,
        canvas: Canvas,
        dx0: int,
        dy0: int,
        lights_on: bool,
        min_py: int = 0,
    ) -> None:
        """Render a stationary ceremonial Little Drummer Boy figurine on the mantelpiece."""
        dim = 1.0 if lights_on else 0.54
        palette: dict[str, RGB] = {
            # Plume, slate-navy velvet bearskin shako, brass star crest & glossy visor
            "w": scale_rgb((252, 248, 240), dim),
            "p": lerp_rgb(STOCKING_RED, STAR_BRIGHT, 0.25 if lights_on else 0.08) if lights_on else scale_rgb(STOCKING_RED, 0.56),
            "k": (34, 38, 54) if lights_on else (24, 28, 42),
            "K": (58, 66, 88) if lights_on else (38, 44, 62),
            "V": (18, 17, 24),
            "G": TINSEL_GOLD if lights_on else scale_rgb(TINSEL_GOLD, 0.52),
            "g": scale_rgb(TINSEL_GOLD, 0.70 * dim),
            # Face & auburn curls
            "h": scale_rgb((96, 56, 34), dim),
            "S": scale_rgb((244, 198, 162), dim),
            "s": scale_rgb((218, 162, 128), dim),
            "E": (22, 20, 32),
            "C": scale_rgb((228, 118, 118), dim),
            # Scarlet ceremonial tunic & crisp white shoulder sling
            "H": scale_rgb((226, 62, 66), dim),
            "R": scale_rgb(STOCKING_RED, dim),
            "r": scale_rgb(STOCKING_RED, 0.58 * dim),
            "W": scale_rgb(CUFF_WHITE, dim),
            # Parade snare drum (vellum head, royal-blue + ivory rope-laced shell) & birch sticks
            "D": scale_rgb((252, 246, 226), dim),
            "d": scale_rgb((204, 188, 158), dim),
            "N": scale_rgb((54, 102, 178), dim),
            "Z": scale_rgb((242, 234, 212), dim),
            "T": scale_rgb((228, 184, 116), dim),
            "t": scale_rgb((118, 74, 38), dim),
            # Glossy Hessian leather boots & carved walnut figurine plinth
            "L": (28, 28, 40) if lights_on else (20, 20, 30),
            "l": (84, 88, 112) if lights_on else (52, 56, 74),
            "M": scale_rgb(MANTEL_WOOD, 1.0 if lights_on else 0.72),
            "m": scale_rgb(MANTEL_WOOD, 0.64 * (1.0 if lights_on else 0.72)),
        }

        sprite = [
            "...p...",  # py = 10  scarlet feather plume tip
            "..kwk..",  # py = 11  white plume tuft framed by bearskin crown
            "..KGK..",  # py = 12  bearskin shako & polished brass badge
            ".VgGgV.",  # py = 13  peaked visor brim & brass chinstrap braid
            ".hEsEh.",  # py = 14  auburn curls, expressive eyes & skin bridge
            "..CSC..",  # py = 15  rosy winter cheeks & warm chin
            ".GRWRG.",  # py = 16  gold shoulder epaulettes, white collar & scarlet throat
            "rWRGRWr",  # py = 17  white V-straps, royal scarlet coat & center brass button
            "sTRWRHr",  # py = 18  stationary left stick poised & white strap taper
            ".dDDDtS",  # py = 19  ivory vellum drumhead & resting drumstick tip
            ".gZNZg.",  # py = 20  brass drum hoops + royal-blue & ivory rope-laced cylinder
            ".rW.Wr.",  # py = 21  scarlet coat-tails framing crisp white breeches
            ".lL.lL.",  # py = 22  tall black Hessian boots with leather highlight
            "mMMGMMm",  # py = 23  turned walnut display plinth with brass nameplate
        ]

        _draw_sprite_shadow_clipped(canvas, dx0, dy0, sprite, 0.48 if lights_on else 0.36, min_py=min_py)
        _draw_sprite_clipped(canvas, dx0, dy0, sprite, palette, min_py=min_py)

    def _draw_mantel_snowglobe(
        self,
        canvas: Canvas,
        sx: int,
        sy: int,
        lights_on: bool,
        min_py: int = 0,
    ) -> None:
        """Render a domed glass winter snowglobe on a turned walnut pedestal."""
        palette = {
            "W": CUFF_WHITE if lights_on else scale_rgb(CUFF_WHITE, 0.56),
            "w": (196, 212, 226) if lights_on else (112, 124, 140),
            "s": (122, 152, 184) if lights_on else (64, 80, 102),
            "S": (86, 114, 146) if lights_on else (48, 60, 78),
            "g": PINE_LIGHT if lights_on else PINE_MID,
            "G": PINE_DARK,
            "M": TINSEL_GOLD if lights_on else scale_rgb(TINSEL_GOLD, 0.45),
            "B": MANTEL_WOOD,
            "D": (42, 26, 20),
        }
        sprite = [
            ".sWs.",
            "sWgss",
            "sgGws",
            "SWWWS",
            "BMMBB",
            ".DBD.",
        ]
        _draw_sprite_clipped(canvas, sx, sy, sprite, palette, min_py=min_py)

    def _draw_mantel_garland(
        self,
        canvas: Canvas,
        x0: int,
        mantel_py: int,
        lights_on: bool,
        warm_p: float = 1.0,
        min_py: int = 0,
    ) -> None:
        """Render pine swags, frosted pinecones, holly berries, and ribbon bows."""
        for sx0, sx1 in ((x0 + 1, x0 + 9), (x0 + 9, x0 + 16), (x0 + 16, x0 + 24)):
            mid = (sx0 + sx1) / 2.0
            half = (sx1 - sx0) / 2.0
            for gx in range(sx0, sx1 + 1):
                curve = 1.0 - ((gx - mid) / half) ** 2
                base_py = int(round((mantel_py - 1.4) + 2.3 * curve))
                is_belly = curve > 0.45
                top_py = base_py - 1 if is_belly else base_py
                bot_py = base_py + 1
                gx_lit = is_warm_lit(gx, base_py, lights_on, warm_p)
                dim = 1.0 if gx_lit else 0.50
                p_light, p_mid, p_dark = scale_rgb(PINE_LIGHT, dim), scale_rgb(PINE_MID, dim), scale_rgb(PINE_DARK, dim)

                if top_py >= min_py:
                    canvas.set_px(gx, top_py, p_light if (gx + top_py) % 3 != 0 else p_mid)
                if is_belly and base_py >= min_py:
                    canvas.set_px(gx, base_py, p_mid)
                if bot_py >= min_py:
                    warm_t = max(0.0, 1.0 - abs(gx - (x0 + 12.5)) / 10.0) * (0.28 if gx_lit else 0.0)
                    canvas.set_px(gx, bot_py, lerp_rgb(p_dark, FIRE_PALETTE[2], warm_t))
                if bot_py + 1 >= min_py:
                    canvas.blend_px(gx, bot_py + 1, SHADOW_PLUM, 0.55)

        self._draw_garland_accents(canvas, x0, mantel_py, lights_on, warm_p, min_py)

    def _draw_garland_accents(
        self,
        canvas: Canvas,
        x0: int,
        mantel_py: int,
        lights_on: bool,
        warm_p: float,
        min_py: int,
    ) -> None:
        """Render pinecones, clustered holly berries, and brass-bell ribbon bows on the garland."""
        for px_c in (x0 + 9, x0 + 16):
            cy = mantel_py - 3
            c_lit = is_warm_lit(px_c, cy, lights_on, warm_p)
            cone_hi = (196, 152, 114) if c_lit else (108, 84, 66)
            cone_mid = (132, 82, 52) if c_lit else (78, 50, 34)
            cone_dark = (72, 42, 26)
            for dy, left_c, mid_c, right_c in (
                (0, cone_dark, cone_hi, cone_dark),
                (1, cone_mid, cone_hi, cone_mid),
                (2, cone_dark, cone_mid, cone_dark),
            ):
                if cy + dy >= min_py:
                    canvas.set_px(px_c - 1, cy + dy, left_c)
                    canvas.set_px(px_c, cy + dy, mid_c)
                    canvas.set_px(px_c + 1, cy + dy, right_c)

        for bx in (x0 + 5, x0 + 12, x0 + 20):
            b_lit = is_warm_lit(bx, mantel_py, lights_on, warm_p)
            berry_main = STOCKING_RED if b_lit else scale_rgb(STOCKING_RED, 0.52)
            berry_hi = lerp_rgb(STOCKING_RED, STAR_BRIGHT, 0.36) if b_lit else berry_main
            if mantel_py >= min_py:
                canvas.set_px(bx, mantel_py, berry_hi)
                canvas.set_px(bx + 1, mantel_py, berry_main)
            if mantel_py + 1 >= min_py:
                canvas.set_px(bx, mantel_py + 1, berry_main)

        for rx in (x0, x0 + 23):
            r_lit = is_warm_lit(rx, mantel_py, lights_on, warm_p)
            berry_main = STOCKING_RED if r_lit else scale_rgb(STOCKING_RED, 0.52)
            berry_hi = lerp_rgb(STOCKING_RED, STAR_BRIGHT, 0.36) if r_lit else berry_main
            bell_col = TINSEL_GOLD if r_lit else scale_rgb(TINSEL_GOLD, 0.48)
            if mantel_py >= min_py:
                canvas.set_px(rx, mantel_py, berry_main)
                canvas.set_px(rx + 1, mantel_py, bell_col)
            if mantel_py + 1 >= min_py:
                canvas.set_px(rx, mantel_py + 1, berry_hi)
                canvas.set_px(rx + 1, mantel_py + 1, berry_main)

    def _draw_stocking(
        self,
        canvas: Canvas,
        sx: int,
        sy_py: int,
        color: tuple[int, int, int],
        face_right: bool,
        lights_on: bool,
        warm_p: float = 1.0,
        min_py: int = 0,
    ) -> None:
        """Draw a stationary Fair Isle knit stocking with brass hook, plump cuff, heel, and toe cap."""
        sock_lit = is_warm_lit(sx + 2, sy_py + 5, lights_on, warm_p)
        palette = {
            "G": TINSEL_GOLD if sock_lit else scale_rgb(TINSEL_GOLD, 0.55),
            "W": CUFF_WHITE,
            "w": (182, 176, 178),
            "H": lerp_rgb(color, STAR_BRIGHT, 0.22 if sock_lit else 0.04),
            "M": color,
            "S": scale_rgb(color, 0.66),
            "K": (236, 224, 196),
            "P": (232, 222, 210),
            "p": (172, 164, 162),
            "F": lerp_rgb(color, FIRE_PALETTE[3], 0.48 if sock_lit else 0.10),
        }

        sprite = [
            ".G...",
            "WWWw.",
            "WWWw.",
            "www..",
            "HMH..",
            "KMK..",
            "MKM..",
            "PMHS.",
            "pMMHP",
            ".SMFP",
            "..FFp",
        ]
        if not face_right:
            sprite = [row[::-1] for row in sprite]

        # Soft drop shadow behind stocking on the brick pier
        for dy, row_str in enumerate(sprite[1:], start=1):
            if sy_py + dy + 1 < min_py:
                continue
            for dx, tok in enumerate(row_str):
                if tok != ".":
                    canvas.blend_px(sx + dx + 1, sy_py + dy + 1, SHADOW_PLUM, 0.32)

        _draw_sprite_clipped(canvas, sx, sy_py, sprite, palette, min_py=min_py)

    def _draw_fire(
        self,
        canvas: Canvas,
        fx: int,
        fy_py: int,
        t: float,
        lights_on: bool,
        fire_p: float = 1.0,
        min_py: int = 0,
        ember_p: float = 1.0,
    ) -> None:
        """Render ember bed, crossed charred logs, curling flame tongues, and sparks."""
        self._draw_embers_and_logs(canvas, fx, fy_py, t, lights_on, min_py, ember_p)
        if not lights_on or fire_p <= 0.02:
            return
        min_flame_dy = int(round((self.fire_px_h - 3) * (1.0 - (1.0 - (1.0 - min(1.0, fire_p)) ** 2))))
        self._draw_flame_plumes(canvas, fx, fy_py, t, min_flame_dy)
        self._draw_rising_sparks(canvas, fx, fy_py, t, min_flame_dy)

    def _draw_embers_and_logs(
        self,
        canvas: Canvas,
        fx: int,
        fy_py: int,
        t: float,
        lights_on: bool,
        min_py: int,
        ember_p: float,
    ) -> None:
        """Render glowing coal bed, iron andiron feet, and cracked charred logs."""
        h, w = self.fire_px_h, self.fire_w
        coal_py = fy_py + h - 2
        coal_glow = max(0.0, min(1.0, ember_p)) if lights_on else 0.0

        for x in range(w):
            pulse = 0.65 + 0.35 * math.sin(t * 3.8 + x * 1.3)
            cold_col = scale_rgb(FIRE_PALETTE[0], 0.55 * pulse)
            hot_col = lerp_rgb(FIRE_PALETTE[0], FIRE_PALETTE[3], pulse * (0.75 if 2 <= x <= w - 3 else 0.35))
            if coal_py + 1 >= min_py:
                canvas.set_px(fx + x, coal_py + 1, lerp_rgb(cold_col, hot_col, coal_glow) if coal_glow > 0.0 else cold_col)
            if 1 <= x <= w - 2 and coal_py >= min_py:
                canvas.set_px(fx + x, coal_py, lerp_rgb(LOG_WOOD, FIRE_PALETTE[2], pulse * (0.25 + 0.35 * coal_glow)))

        bark_hi = lerp_rgb(LOG_WOOD, FLOOR_WOOD_LIGHT, coal_glow)
        log_spans = ((h - 4, 2, 5, True), (h - 3, 1, 6, False), (h - 4, 7, 10, True), (h - 3, 6, 10, False), (h - 2, 2, 9, False))
        for py_off, xs, xe, is_top in log_spans:
            py = fy_py + py_off
            if py < min_py:
                continue
            for x in range(xs, xe + 1):
                if is_top:
                    col = lerp_rgb(LOG_WOOD, bark_hi, 0.15 + 0.40 * coal_glow)
                elif x in (xs, xe):
                    col = lerp_rgb(bark_hi, FIRE_PALETTE[2], 0.12 + 0.33 * coal_glow)
                else:
                    col = (38, 22, 16)
                canvas.set_px(fx + x, py, col)

        for cx, cy_off, phase in ((3, h - 3, 0.4), (5, h - 2, 1.8), (8, h - 3, 3.1), (4, h - 2, 4.4)):
            py = fy_py + cy_off
            if py >= min_py:
                glow = 0.5 + 0.5 * math.sin(t * 4.5 + phase)
                canvas.set_px(fx + cx, py, lerp_rgb(FIRE_PALETTE[0], lerp_rgb(FIRE_PALETTE[1], FIRE_PALETTE[4], coal_glow), glow))

        for ax in (1, w - 2):
            if fy_py + h - 2 >= min_py:
                canvas.set_px(fx + ax, fy_py + h - 2, (36, 34, 44))
            if fy_py + h - 1 >= min_py:
                canvas.set_px(fx + ax, fy_py + h - 1, (54, 52, 64))

    def _draw_flame_plumes(self, canvas: Canvas, fx: int, fy_py: int, t: float, min_flame_dy: int) -> None:
        """Render multi-plume animated fire tongues above the logs."""
        h, w = self.fire_px_h, self.fire_w
        plumes = ((5.5, 4.2, 12.8, 6.4, 0.0), (2.8, 2.3, 8.8, 7.6, 1.9), (8.2, 2.4, 9.4, 7.1, 3.7))
        for dy in range(min_flame_dy, h - 3):
            y_from_logs = (h - 3) - dy
            for x in range(w):
                best_heat = 0.0
                for cx, base_w, max_h, spd, ph in plumes:
                    u = y_from_logs / max_h
                    if u > 1.15:
                        continue
                    sway = math.sin(t * spd - u * 4.2 + ph) * (0.45 + u * 1.15)
                    turb = math.cos(t * (spd * 1.45) - u * 6.5 + ph) * 0.35 * u
                    width_at_y = base_w * max(0.08, 1.0 - 0.78 * (u ** 0.85))
                    best_heat = max(best_heat, (1.0 - abs(x - (cx + sway + turb)) / width_at_y) * (1.0 - 0.58 * (u ** 1.15)))

                wisp_y = 2.0 + 1.5 * math.sin(t * 5.2)
                if abs(dy - wisp_y) < 0.7 and abs(x - (5.5 + math.sin(t * 6.8) * 1.6)) < 0.75:
                    best_heat = max(best_heat, 0.38)

                if best_heat > 0.14:
                    norm = min(1.0, (best_heat - 0.14) / 0.86)
                    idx = min(len(FIRE_PALETTE) - 1, int(round(norm * (len(FIRE_PALETTE) - 1))))
                    canvas.set_px(fx + x, fy_py + dy, FIRE_PALETTE[idx])

    def _draw_rising_sparks(self, canvas: Canvas, fx: int, fy_py: int, t: float, min_flame_dy: int) -> None:
        """Render looping glowing sparks drifting upward into the firebox crown."""
        ticks = t * 20.0
        ember_span = self.fire_px_h - 4.5
        for idx, ember in enumerate(self.embers):
            dist_up = (ember_span - float(ember[1])) + float(ember[2]) * ticks
            cycle = int(dist_up // ember_span)
            base_x = float(ember[0]) if cycle == 0 else (2.0 + hash01(idx, cycle) * (self.fire_w - 5.0))
            ey = int(round(ember_span - (dist_up % ember_span)))
            ex = int(round(base_x + math.sin(t * 4.5 + float(ember[3])) * float(ember[4])))
            if min_flame_dy <= ey < self.fire_px_h - 3 and 0 <= ex < self.fire_w:
                canvas.set_px(fx + ex, fy_py + ey, FIRE_PALETTE[-1] if ey > 3 else FIRE_PALETTE[-2])
