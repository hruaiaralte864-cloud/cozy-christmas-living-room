"""Foreground living-room furnishings: ceiling lights, oak bookcase, retro radio, curtains, chair, and cat."""

from __future__ import annotations

import math

from .canvas import Canvas
from .palette import (
    CHAIR_CUSHION,
    CHAIR_FABRIC,
    CHAIR_SHADOW,
    CURTAIN_LIGHT,
    CURTAIN_MAIN,
    CURTAIN_SHADOW,
    FLOOR_MOON_GLOW,
    FLOOR_WARM_GLOW,
    FLOOR_WOOD_LIGHT,
    LIGHT_COLORS,
    PINE_DARK,
    PINE_LIGHT,
    PINE_MID,
    RGB,
    RUG_CREAM,
    SHADOW_PLUM,
    SNOW_WHITE,
    STAR_BRIGHT,
    STAR_GLOW,
    STOCKING_RED,
    TABLE_WOOD,
    TINSEL_GOLD,
    WALL_TREE_GLOW,
    lerp_rgb,
    scale_rgb,
)
from .room import is_warm_lit


def _build_bookcase_palette(shelf_lit: bool) -> dict[str, RGB]:
    """Return static RGB lookup dictionary for lit or dimmed oak bookcase props."""
    return {
        "I": (40, 38, 48),
        "G": PINE_MID,
        "L": PINE_LIGHT,
        "g": PINE_DARK,
        "B": TINSEL_GOLD,
        "b": (168, 128, 62),
        "H": lerp_rgb(STOCKING_RED, STAR_BRIGHT, 0.25),
        "R": STOCKING_RED,
        "r": scale_rgb(STOCKING_RED, 0.66),
        "N": (52, 74, 114),
        "n": (38, 54, 86),
        "P": RUG_CREAM,
        "p": scale_rgb(RUG_CREAM, 0.76),
        "a": (124, 166, 180),
        "U": (86, 128, 144),
        "u": (56, 88, 104),
        "C": (232, 222, 202),
        "k": (174, 164, 152),
        "T": (182, 128, 72),
        "t": (132, 88, 48),
        "d": (26, 22, 28),
        "S": SNOW_WHITE,
        "s": (172, 182, 196),
        "W": STAR_BRIGHT if shelf_lit else (48, 60, 78),
        "Y": STAR_GLOW if shelf_lit else (34, 44, 60),
        "O": lerp_rgb(STAR_GLOW, FLOOR_WARM_GLOW, 0.45) if shelf_lit else (24, 32, 46),
    }


_BOOKCASE_PALETTE_LIT = _build_bookcase_palette(True)
_BOOKCASE_PALETTE_DIM = _build_bookcase_palette(False)

_UPPER_SHELF_PROPS: tuple[str, ...] = (
    "..HR.LG..........",
    "..BBPLG..........",
    "..HRBBBP...RHRR..",
    ".IHRPLGTP..PPPr..",
    ".IBBPLG.Tt.NnNNN.",
    ".IrrpGg.tT.NPPPP.",
)

_LOWER_SHELF_PROPS: tuple[str, ...] = (
    "..........S......",
    ".........s.......",
    "........s........",
    "..aUUUUUs...Nn...",
    ".UkkkCYRWOu.NnPR.",
    ".UdddCIIIIu.BBTR.",
    ".UkkkCIBIBu.NnPB.",
    ".uuuuuuuuuu.NnPR.",
    "..b......b..nNpr.",
)

_LEFT_CURTAIN_SPRITE: tuple[str, ...] = (
    "RLMCLM",
    "RLSCRC",
    "RMSMLC",
    "RLMCLM",
    "RLMSLC",
    "RMSMRC",
    "RMLMSC",
    ".RMSLC",
    ".RLMSC",
    ".RMSMC",
    ".RLMS.",
    ".RMSM.",
    ".RMLC.",
    ".gGGg.",
    ".GGg..",
    ".gRMS.",
    "RMSMLC",
    "RLMSMC",
    "RLMCLC",
    "RMSMLC",
    "RLMSLC",
    "RMSMLC",
    "RLMSMC",
    "RMSMLC",
    "RLMSLC",
    "SMSCLC",
    "RLMSMC",
    "RMSMLC",
    "RLMSMC",
    ".L.L.M",
)

_RIGHT_CURTAIN_SPRITE: tuple[str, ...] = (
    ".MLCMR",  # keeps glass x <= 110 clear
    ".CSCLR",
    ".MLSML",
    ".CLSMR",
    ".CMSMR",
    ".CLSMR",
    ".CMSML",
    "..LSML",
    "..CMSR",
    "..LSML",
    "..CMS.",
    "..LSM.",
    "..CMS.",
    "..gGGg",
    "...gGG",
    "..LMSg",
    ".CLSMR",
    ".CMSMR",
    ".CLSMR",
    "CLMSMR",
    "CMSMLR",
    "CLMSMR",
    "CMSMLR",
    "CLMSMR",
    "CMSMLR",
    "CSCSCR",
    "CLMSMR",
    "CMSMLR",
    "CLMSMR",
    "M.L.L.",
)

_CHAIR_SPRITE: tuple[str, ...] = (
    ".......WWWWWHHHHHHBB....",
    "......WHHHHMMMMMMMHMB...",
    ".....WWHMMMMDMMMMDMMMB..",
    ".....WMHMHMMMMMMMMMMMB..",
    "....WWHMDMMMMMMMDMMMMBB.",
    "....WHMMHMMppPPPMMMMMDB.",
    "....WMMMDMPPPPPpMMMMDDB.",
    "...WWHHMDMPPPPPppMMMDDB.",
    "..WWHHHMDMPPPPppDDMMDDB.",
    "..WHMMHMDDHHHppHHHMMDDDB",
    ".WWHMMMCMHHHHHHHMHMDDDDB",
    ".WHHHMMCHHHHHHHHHMMMDDDB",
    ".WHMMHMCHHHHHHHHMMMMDDDB",
    ".WMMMMMCHHHHHMMMHMMMDDDB",
    ".WMMMCDCCHMMMMMMHMMMDDDB",
    ".WDMDDDCCCCCCCCMMMDDDDl.",
    "..WDDDDLLCCCCCCDDDDDDll.",
    "..WDDDDDLLLLLLLDDDDDll..",
    "...DDDDDLLllDDDDDDllll..",
    "....LL........LL...ll...",
    "....Ll........Ll...l....",
    "....Ll........l.........",
    ".....l..................",
)


def draw_wall_decorations(
    canvas: Canvas,
    t: float,
    progress: float = 1.0,
    lights_on: bool = True,
    ceiling_lights_p: float = 1.0,
    bookcase_p: float = 1.0,
    furniture_p: float = 1.0,
    warm_p: float = 1.0,
    fire_lit: bool = True,
    electric_p: float = 1.0,
) -> None:
    """Render overhead lights, bookcase with radio, drapes, wingback chair, and cat."""
    if progress < 0.05:
        return

    el_lit = lights_on and electric_p > 0.05
    furn_warm_p = warm_p * electric_p if (el_lit and electric_p < 1.0) else warm_p
    if ceiling_lights_p > 0.02 or progress >= 0.55:
        wire_p = 1.0 if (lights_on or progress >= 0.92) else max(0.0, min(1.0, (progress - 0.55) / 0.37))
        _draw_ceiling_lights(canvas, t, lights_on=el_lit, sweep_p=ceiling_lights_p, wire_p=wire_p)
    if bookcase_p > 0.02:
        _draw_wall_bookcase(
            canvas,
            t=t,
            lights_on=el_lit,
            reveal_p=bookcase_p,
            warm_p=warm_p,
            fire_lit=fire_lit,
            electric_p=electric_p,
        )
    if furniture_p > 0.02:
        _draw_window_curtains(canvas, lights_on=el_lit, reveal_p=furniture_p, warm_p=furn_warm_p)
        chair_p = max(0.0, min(1.0, (furniture_p - 0.18) / 0.58))
        if chair_p > 0.01:
            chair_min_py = 0 if chair_p >= 1.0 else 59 - int(round(23.0 * (1.0 - (1.0 - chair_p) ** 2)))
            _draw_wingback_chair(
                canvas,
                lights_on=el_lit and electric_p >= 0.55 and is_warm_lit(95, 48, True, furn_warm_p),
                min_py=chair_min_py,
            )
        cat_p = max(0.0, min(1.0, (furniture_p - 0.62) / 0.38))
        if cat_p > 0.01:
            cat_min_py = 0 if cat_p >= 1.0 else 51 - int(round(9.0 * (1.0 - (1.0 - cat_p) ** 2)))
            _draw_chair_cat(
                canvas,
                t=t,
                lights_on=el_lit and electric_p >= 0.55 and is_warm_lit(98, 46, True, furn_warm_p),
                min_py=cat_min_py,
            )


def _draw_ceiling_lights(
    canvas: Canvas,
    t: float,
    lights_on: bool,
    sweep_p: float = 1.0,
    wire_p: float = 1.0,
) -> None:
    """Render sagging ceiling cable and twinkling fairy-light bulbs."""
    w = canvas.width
    wire_limit_x = w if wire_p >= 1.0 else int(round(w * max(0.0, min(1.0, wire_p))))
    lit_limit_x = w if sweep_p >= 1.0 else int(round(w * max(0.0, min(1.0, sweep_p))))
    for x in range(w):
        if wire_p < 1.0 and x > wire_limit_x:
            break
        if 8 <= x <= 23:
            continue
        phase = (x / max(1, w - 1)) * 5.0 * math.pi
        sag_px = 3 + int(round(abs(math.sin(phase)) * 2.2))
        if 48 <= x <= 68:
            arch = max(0.0, 1.0 - abs(x - 58) / 10.0)
            sag_px = min(sag_px, max(2, int(round(4 - 2 * arch))))
        canvas.set_px(x, sag_px, (48, 44, 52))

        if 3 <= x <= w - 4 and x % 5 == 0:
            idx = (x // 5) % len(LIGHT_COLORS)
            base = LIGHT_COLORS[idx]
            if lights_on and x <= lit_limit_x:
                raw_pulse = 0.58 + 0.42 * math.sin(t * 3.8 + x * 0.45)
                pulse = round(raw_pulse * 6.0) / 6.0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        dist = math.hypot(dx, dy)
                        if dist <= 1.4:
                            canvas.blend_px(x + dx, sag_px + dy, base, (0.36 - dist * 0.16) * pulse)
                canvas.set_px(x, sag_px, scale_rgb(base, min(1.2, pulse + 0.4)))
                if pulse > 0.85:
                    canvas.set_px(x, sag_px, STAR_BRIGHT)
            else:
                canvas.set_px(x, sag_px, scale_rgb(base, 0.25))


def _draw_wall_bookcase(
    canvas: Canvas,
    t: float,
    lights_on: bool,
    reveal_p: float = 1.0,
    warm_p: float = 1.0,
    fire_lit: bool = True,
    electric_p: float = 1.0,
) -> None:
    """Render two-tier floating oak bookcase, Slate-Teal retro radio, and song notes."""
    ep = max(0.0, min(1.0, electric_p))
    low_lit = is_warm_lit(37, 25, lights_on and ep > 0.15, warm_p)
    up_lit = is_warm_lit(37, 13, lights_on and ep > 0.25, warm_p)
    edge_hearth = (fire_lit and warm_p > 0.25) and not low_lit

    up_p = max(0.0, min(1.0, (reveal_p - 0.36) / 0.64))
    if up_p > 0.01:
        up_min_py = 0 if up_p >= 1.0 else 18 - int(round(10.0 * (1.0 - (1.0 - up_p) ** 2)))
        _draw_floating_oak_shelf(
            canvas,
            x0=29,
            py_ledge=14,
            props_sprite=_UPPER_SHELF_PROPS,
            prop_palette=_BOOKCASE_PALETTE_LIT if up_lit else _BOOKCASE_PALETTE_DIM,
            bright=1.0 if up_lit else 0.56,
            lights_on=up_lit,
            min_py=up_min_py,
            edge_hearth=edge_hearth,
        )

    low_p = max(0.0, min(1.0, reveal_p / 0.58))
    if low_p <= 0.01:
        return
    low_min_py = 0 if low_p >= 1.0 else 31 - int(round(13.0 * (1.0 - (1.0 - low_p) ** 2)))

    if low_lit and low_p >= 0.55:
        dial_glow = min(1.0, ep * 1.45)
        for wy in range(max(21, low_min_py), 25):
            for wx in range(34, 40):
                dist = math.hypot((wx - 36.5) * 0.85, (wy - 22.0) * 1.2)
                if dist <= 2.3:
                    canvas.blend_px(wx, wy, FLOOR_WARM_GLOW, (1.0 - dist / 2.5) * 0.14 * dial_glow)

    _draw_floating_oak_shelf(
        canvas,
        x0=29,
        py_ledge=27,
        props_sprite=_LOWER_SHELF_PROPS,
        prop_palette=_BOOKCASE_PALETTE_LIT if low_lit else _BOOKCASE_PALETTE_DIM,
        bright=1.0 if low_lit else 0.56,
        lights_on=low_lit,
        min_py=low_min_py,
        edge_hearth=edge_hearth,
    )

    if low_lit and low_p >= 1.0 and ep >= 0.55:
        _draw_radio_music_animation(canvas, t)


def _draw_radio_music_animation(canvas: Canvas, t: float) -> None:
    """Render beat LED, speaker diaphragm pulse, and two-phrase floating eighth/quarter notes."""
    beat = int(t * 2.4) % 4
    beat_strength = 1.0 if beat == 0 else (0.55 if beat == 2 else 0.20)
    led_col = (188, 242, 148) if beat in (0, 2) else (98, 152, 90)
    canvas.set_px(35, 23, lerp_rgb((44, 42, 52), led_col, 0.45 + 0.55 * beat_strength))
    if beat in (0, 2):
        canvas.blend_px(32, 23, (126, 112, 102), 0.52 if beat == 0 else 0.28)

    cycle = (t * 0.35) % 1.0
    cream_hi: RGB = (255, 244, 204)
    gold_mid: RGB = (246, 204, 132)
    amber_lo: RGB = (198, 142, 82)
    note_pixels: tuple[tuple[int, int, RGB, float], ...] | None = None
    nx, ny, fade = 34, 17, 0.0

    if cycle < 0.48:
        note_pixels = (
            (1, 0, gold_mid, 0.88),
            (1, 1, gold_mid, 0.88),
            (2, 1, amber_lo, 0.75),
            (0, 2, cream_hi, 0.95),
            (1, 2, gold_mid, 0.92),
        )
        nx, ny, fade = (33, 18, 0.45) if cycle < 0.16 else ((34, 17, 0.95) if cycle < 0.36 else (34, 17, 0.45))
    elif 0.52 <= cycle < 0.93:
        note_pixels = (
            (1, 0, gold_mid, 0.80),
            (1, 1, gold_mid, 0.80),
            (0, 2, cream_hi, 0.90),
            (1, 2, amber_lo, 0.78),
        )
        nx, ny, fade = (35, 18, 0.48) if cycle < 0.68 else ((35, 17, 0.82) if cycle < 0.84 else (35, 17, 0.38))

    if note_pixels is not None:
        for dx, dy, ncol, rel_a in note_pixels:
            canvas.blend_px(nx + dx, ny + dy, ncol, rel_a * fade)


def _draw_shelf_shadows(
    canvas: Canvas,
    x0: int,
    py_ledge: int,
    shelf_w: int,
    props_sprite: tuple[str, ...],
    min_py: int,
) -> None:
    """Cast soft (+1, +1) drop shadows behind shelf props, ledge, and brackets."""
    top_py = py_ledge - len(props_sprite)
    for dy, row in enumerate(props_sprite):
        py = top_py + dy
        if py + 1 < min_py:
            continue
        for dx, ch in enumerate(row):
            if ch != ".":
                canvas.blend_px(x0 + dx + 1, py + 1, SHADOW_PLUM, 0.36)

    for dx in range(shelf_w):
        px = x0 + dx
        if py_ledge + 1 >= min_py:
            canvas.blend_px(px + 1, py_ledge + 1, SHADOW_PLUM, 0.44)
        if py_ledge + 2 >= min_py:
            canvas.blend_px(px + 1, py_ledge + 2, SHADOW_PLUM, 0.46)
    for bx in (x0 + 2, x0 + shelf_w - 4):
        if py_ledge + 2 >= min_py:
            canvas.blend_px(bx + 2, py_ledge + 2, SHADOW_PLUM, 0.42)
        if py_ledge + 3 >= min_py:
            canvas.blend_px(bx + 1, py_ledge + 3, SHADOW_PLUM, 0.42)
        if py_ledge + 4 >= min_py:
            canvas.blend_px(bx + 1, py_ledge + 4, SHADOW_PLUM, 0.35)


def _draw_floating_oak_shelf(
    canvas: Canvas,
    x0: int,
    py_ledge: int,
    props_sprite: tuple[str, ...],
    prop_palette: dict[str, RGB],
    bright: float,
    lights_on: bool,
    min_py: int = 0,
    edge_hearth: bool = False,
) -> None:
    """Render a 17-col floating oak shelf with corbel brackets, drop shadows, and props."""
    shelf_w = 17
    oak_top = lerp_rgb(TABLE_WOOD, FLOOR_WOOD_LIGHT, 0.42)
    oak_mid = TABLE_WOOD
    oak_shade = scale_rgb(TABLE_WOOD, 0.78)
    corbel_dark = scale_rgb(TABLE_WOOD, 0.56)

    _draw_shelf_shadows(canvas, x0, py_ledge, shelf_w, props_sprite, min_py)

    top_py = py_ledge - len(props_sprite)
    for dy, row in enumerate(props_sprite):
        py = top_py + dy
        if py < min_py:
            continue
        for dx, ch in enumerate(row):
            if ch == ".":
                continue
            col = prop_palette[ch]
            grad = max(0.0, 1.0 - dx / 10.0)
            if grad > 0.0 and (lights_on or edge_hearth):
                col = lerp_rgb(col, FLOOR_WARM_GLOW, (0.24 if edge_hearth else 0.16) * grad)
            if py == py_ledge - 1:
                col = lerp_rgb(col, SHADOW_PLUM, 0.14)
            loc_bright = bright if (not edge_hearth or grad <= 0.0) else min(0.84, bright + 0.24 * grad)
            canvas.set_px(x0 + dx, py, scale_rgb(col, loc_bright))

    for dx in range(shelf_w):
        px = x0 + dx
        warm = max(0.0, 1.0 - dx / 11.0) * (0.28 if lights_on else (0.34 if edge_hearth else 0.0))
        top_c = lerp_rgb(oak_top, FLOOR_WARM_GLOW, warm)
        if dx == shelf_w - 1:
            top_c = scale_rgb(top_c, 0.88)
        front_base = oak_mid if dx < shelf_w - 5 else oak_shade
        front_c = lerp_rgb(front_base, FLOOR_WARM_GLOW, warm * 0.5)
        if dx in (0, shelf_w - 1):
            front_c = scale_rgb(front_c, 0.86)
        loc_bright = bright if (not edge_hearth or dx > 7) else min(0.86, bright + 0.24 * (1.0 - dx / 8.0))
        if py_ledge >= min_py:
            canvas.set_px(px, py_ledge, scale_rgb(top_c, loc_bright))
        if py_ledge + 1 >= min_py:
            canvas.set_px(px, py_ledge + 1, scale_rgb(front_c, loc_bright))

    for bx, tip_x in ((x0 + 2, x0 + 2), (x0 + shelf_w - 4, x0 + shelf_w - 3)):
        if py_ledge + 2 >= min_py:
            canvas.set_px(bx, py_ledge + 2, scale_rgb(oak_mid, 0.86 * bright))
            canvas.set_px(bx + 1, py_ledge + 2, scale_rgb(corbel_dark, bright))
        if py_ledge + 3 >= min_py:
            canvas.set_px(tip_x, py_ledge + 3, scale_rgb(corbel_dark, 0.85 * bright))


def _draw_window_curtains(
    canvas: Canvas,
    lights_on: bool,
    reveal_p: float = 1.0,
    warm_p: float = 1.0,
) -> None:
    """Render brass curtain rod and pleated velvet window drapes."""
    e = 1.0 - (1.0 - max(0.0, min(1.0, reveal_p))) ** 2
    max_dy = len(_LEFT_CURTAIN_SPRITE) if reveal_p >= 1.0 else int(round(len(_LEFT_CURTAIN_SPRITE) * min(1.0, e * 1.15)))

    rod_p = 1.0 if reveal_p >= 0.24 else max(0.0, min(1.0, reveal_p / 0.24))
    rod_half = int(round(17.0 * (1.0 - (1.0 - rod_p) ** 2)))
    rod_x0 = 80 if reveal_p >= 0.24 else max(80, 96 - rod_half)
    rod_x1 = 113 if reveal_p >= 0.24 else min(113, 97 + rod_half)

    for x in range(rod_x0, rod_x1 + 1):
        lit_px = is_warm_lit(x, 6, lights_on, warm_p)
        bright = 1.0 if lit_px else 0.58
        if x in (80, 113):
            col = TINSEL_GOLD
            canvas.set_px(x, 5, scale_rgb(TINSEL_GOLD, bright * 0.9))
            canvas.set_px(x, 7, scale_rgb(TINSEL_GOLD, bright * 0.72))
        elif x in (81, 83, 85, 110, 112):
            col = TINSEL_GOLD
        else:
            col = scale_rgb(TINSEL_GOLD, 0.72)
        canvas.set_px(x, 6, scale_rgb(col, bright))

    dark_palette: dict[str, RGB] = {
        "R": lerp_rgb(CURTAIN_LIGHT, WALL_TREE_GLOW, 0.06),
        "L": CURTAIN_LIGHT,
        "M": CURTAIN_MAIN,
        "S": lerp_rgb(CURTAIN_MAIN, CURTAIN_SHADOW, 0.58),
        "C": CURTAIN_SHADOW,
        "G": TINSEL_GOLD,
        "g": scale_rgb(TINSEL_GOLD, 0.68),
    }
    lit_palette: dict[str, RGB] = {**dark_palette, "R": lerp_rgb(CURTAIN_LIGHT, WALL_TREE_GLOW, 0.36)}

    for x0, sprite, shadow_dir in ((81, _LEFT_CURTAIN_SPRITE, 1), (108, _RIGHT_CURTAIN_SPRITE, -1)):
        for dy, row_str in enumerate(sprite[:max_dy]):
            py = 7 + dy
            for dx, token in enumerate(row_str):
                if token == ".":
                    continue
                px = x0 + dx
                lit_px = is_warm_lit(px, py, lights_on, warm_p)
                pal = lit_palette if lit_px else dark_palette
                canvas.set_px(px, py, scale_rgb(pal[token], 1.0 if lit_px else 0.58))
                next_dx = dx + shadow_dir
                if not (0 <= next_dx < len(row_str)) or row_str[next_dx] == ".":
                    canvas.blend_px(px + shadow_dir, py, SHADOW_PLUM, 0.28)


def _draw_wingback_chair(canvas: Canvas, lights_on: bool, min_py: int = 0) -> None:
    """Render wingback armchair beside the window facing toward the tree."""
    bright = 1.0 if lights_on else 0.58
    x0, py0 = 87, 36
    palette: dict[str, RGB] = {
        "W": lerp_rgb(CHAIR_CUSHION, FLOOR_WARM_GLOW, 0.48 if lights_on else 0.10),
        "H": CHAIR_CUSHION,
        "M": CHAIR_FABRIC,
        "D": lerp_rgb(CHAIR_FABRIC, CHAIR_SHADOW, 0.55),
        "C": lerp_rgb(CHAIR_SHADOW, SHADOW_PLUM, 0.45),
        "B": lerp_rgb(CHAIR_SHADOW, FLOOR_MOON_GLOW, 0.36 if not lights_on else 0.22),
        "P": lerp_rgb((232, 218, 198), FLOOR_WARM_GLOW, 0.14 if lights_on else 0.0),
        "p": (176, 152, 134),
        "L": FLOOR_WOOD_LIGHT if lights_on else TABLE_WOOD,
        "l": scale_rgb(TABLE_WOOD, 0.65),
    }

    for row_idx, (sx, span) in enumerate(((4, 17), (5, 17), (7, 15), (9, 11))):
        py = py0 + 19 + row_idx
        if py >= min_py:
            for dx in range(span):
                canvas.blend_px(x0 + sx + dx, py, SHADOW_PLUM, 0.46 - row_idx * 0.06)

    for dy, row_str in enumerate(_CHAIR_SPRITE):
        py = py0 + dy
        if py < min_py:
            continue
        for dx, token in enumerate(row_str):
            if token != ".":
                canvas.set_px(x0 + dx, py, scale_rgb(palette[token], bright))


def _cat_pose_rows(
    head_up: bool,
    inhale: bool,
    eye_peek: bool,
    slow_blink: bool,
    paw_flex: bool,
    ear_twitch: bool,
) -> list[tuple[int, str]]:
    """Select sub-pixel sprite rows for the animated armchair cat pose."""
    if head_up:
        return [
            (-1, "..R.G....." if ear_twitch else ".R..G....."),
            (0, ".EGHD....."),
            (1, "PGGGG....." if slow_blink else "PYGYG....."),
            (2, ".PPPGRRR.."),
            (3, "..PPwGGGD."),
            (4, "..PPwGGGGD"),
            (5, "...DDDDGGD"),
        ]
    sprite = [
        "..R.G....." if ear_twitch else ".R..G.....",
        ".EGHD.....",
        "PGYHGGRR.." if eye_peek else "PGGHGGRR..",
        ".PwDDGGGD.",
        ".PP.wGGGGD" if paw_flex else "..PPwGGGGD",
        "...DDDDGGD",
    ]
    if inhale:
        sprite[1] = ".EGHDRRR.."
        sprite[2] = "PGYGGGGGD." if eye_peek else "PGGGGGGGD."
    return list(enumerate(sprite))


def _draw_chair_cat(canvas: Canvas, t: float, lights_on: bool, min_py: int = 0) -> None:
    """Render sleeping and peeking tuxedo cat curled on the armchair cushion."""
    bright = 1.0 if lights_on else 0.56
    x0, py0 = 94, 43
    cycle = t % 10.0
    inhale = math.sin(t * 1.55) > 0.25
    head_up = 6.8 <= cycle < 8.8
    tail_phase = int(t * (3.0 if head_up else 2.2)) % 4

    palette: dict[str, RGB] = {
        "R": lerp_rgb((84, 74, 88), STAR_GLOW, 0.34 if lights_on else 0.08),
        "H": lerp_rgb((66, 64, 76), STAR_GLOW, 0.18 if lights_on else 0.0),
        "G": (34, 34, 44),
        "D": (18, 17, 24),
        "P": lerp_rgb((242, 238, 234), STAR_GLOW, 0.10 if lights_on else 0.0),
        "w": (176, 178, 194),
        "E": (214, 136, 144),
        "Y": (250, 206, 86) if lights_on else (188, 166, 84),
    }

    if py0 + 5 >= min_py:
        for dx in range(3, 9):
            canvas.blend_px(x0 + dx, py0 + 5, SHADOW_PLUM, 0.28)
    if py0 + 6 >= min_py:
        for dx in range(2, 9):
            canvas.blend_px(x0 + dx, py0 + 6, SHADOW_PLUM, 0.50)

    rows = _cat_pose_rows(
        head_up=head_up,
        inhale=inhale,
        eye_peek=(5.8 <= cycle < 6.8) or (8.8 <= cycle < 9.3),
        slow_blink=7.7 <= cycle < 7.98,
        paw_flex=inhale and (int(t / 4.0) % 2 == 1),
        ear_twitch=(t % 5.5) < 0.28,
    )
    for dy, row_str in rows:
        py = py0 + dy
        if py < min_py:
            continue
        for dx, token in enumerate(row_str):
            if token != ".":
                canvas.set_px(x0 + dx, py, scale_rgb(palette[token], bright))

    tail_frames: tuple[tuple[tuple[int, int, str], ...], ...] = (
        ((6, 6, "G"), (7, 6, "H"), (7, 7, "w"), (8, 7, "P")),
        ((6, 6, "G"), (7, 6, "H"), (6, 7, "w"), (7, 7, "P")),
        ((5, 6, "G"), (6, 6, "H"), (5, 7, "w"), (6, 7, "P")),
        ((6, 6, "G"), (7, 6, "H"), (6, 7, "w"), (7, 7, "P")),
    )
    for dx, dy, token in tail_frames[tail_phase]:
        py = py0 + dy
        if py >= min_py:
            canvas.set_px(x0 + dx, py, scale_rgb(palette[token], bright))
