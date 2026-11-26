"""Cached room shell architecture: beams, plaster walls, wainscot, floorboards, and Kilim rug."""

from __future__ import annotations

import math

from .canvas import Canvas
from .palette import (
    BASEBOARD,
    CEILING_BEAM,
    CEILING_BEAM_BG,
    FLOOR_BG_DARK,
    FLOOR_MOON_GLOW,
    FLOOR_WARM_GLOW,
    FLOOR_WOOD_LIGHT,
    RGB,
    RUG_COOL,
    RUG_CREAM,
    SHADOW_PLUM,
    STAR_GLOW,
    WAINSCOT,
    WAINSCOT_RECESS,
    WAINSCOT_TRIM,
    WALL_BG,
    WALL_MOON_GLOW,
    WALL_TOP_BG,
    WALL_TREE_GLOW,
    WALL_WARM_GLOW,
    hash01,
    lerp_rgb,
    scale_rgb,
)

BASEBOARD_Y = 26
_FLOOR_SEAM_ROWS = frozenset({54, 57, 61, 65, 69})
_FLOOR_BEVEL_ROWS = frozenset({55, 58, 62, 66})
_STATIC_FLICKER = 0.94

_ROOM_CACHE: dict[tuple[int, int, str, bool], tuple[list[list[RGB]], list[list[RGB]]]] = {}


def is_warm_lit(x: int, py: int, lights_on: bool, warm_p: float) -> bool:
    """Return whether cell (x, py) lies inside the expanding hearth firelight radius."""
    if not lights_on or warm_p <= 0.0:
        return False
    if warm_p >= 1.0:
        return True
    u = warm_p * warm_p * (3.0 - 2.0 * warm_p)
    radius = u * 98.0
    y_cell = py >> 1
    dist = math.hypot((x - 16) * 0.85, (y_cell * 2) - 40)
    if dist <= radius - 3.5:
        return True
    if dist <= radius:
        return ((x + y_cell) & 1) == 0
    if dist <= radius + 2.5:
        return (x & 1) == 0 and (y_cell & 1) == 0
    return False


def warm_up_room_cache(w: int, h: int, default_bg: RGB) -> None:
    """Precompute dark, fire-only, and full-lit static room buffers before the intro loop."""
    _get_room_buffers(w, h, light_mode="dark", include_rug=False, default_bg=default_bg)
    _get_room_buffers(w, h, light_mode="dark", include_rug=True, default_bg=default_bg)
    _get_room_buffers(w, h, light_mode="fire", include_rug=True, default_bg=default_bg)
    _get_room_buffers(w, h, light_mode="full", include_rug=True, default_bg=default_bg)


def _get_room_buffers(
    w: int,
    h: int,
    light_mode: str,
    include_rug: bool,
    default_bg: RGB,
) -> tuple[list[list[RGB]], list[list[RGB]]]:
    """Return cached (top, bot) sub-pixel buffers for a room lighting state."""
    cache_key = (w, h, light_mode, include_rug)
    cached = _ROOM_CACHE.get(cache_key)
    if cached is not None:
        return cached

    scratch = Canvas(w, h, default_bg=default_bg)
    _render_room_pixels(scratch, w, h, include_rug=include_rug, light_mode=light_mode)
    buffers = (
        [row[:] for row in scratch._top_px],
        [row[:] for row in scratch._bot_px],
    )
    _ROOM_CACHE[cache_key] = buffers
    return buffers


def _get_rug_pair(
    w: int,
    h: int,
    light_mode: str,
    rug_span: float,
    default_bg: RGB,
) -> tuple[list[list[RGB]], list[list[RGB]], list[list[RGB]], list[list[RGB]]]:
    """Fetch paired with-rug and no-rug room buffers for partial carpet reveal."""
    with_t, with_b = _get_room_buffers(w, h, light_mode=light_mode, include_rug=True, default_bg=default_bg)
    if rug_span < 1.0:
        no_t, no_b = _get_room_buffers(w, h, light_mode=light_mode, include_rug=False, default_bg=default_bg)
        return no_t, no_b, with_t, with_b
    return with_t, with_b, with_t, with_b


def _rug_row_bounds(py: int, w: int, rug_span: float) -> tuple[int, int] | None:
    """Return horizontal [vx0, vx1] carpet bounds for sub-pixel row py, or None outside."""
    cx = 57.0
    if 53 <= py <= 65:
        half_w = 34.0 + ((py - 53) / 12.0) * 12.0
        vis_half = half_w * min(1.0, rug_span)
        vx0 = max(max(2, int(round(cx - half_w))), int(round(cx - vis_half)))
        vx1 = min(min(w - 2, int(round(cx + half_w))), int(round(cx + vis_half)))
        if 53 < py < 65 and rug_span >= 0.96:
            vx0 = max(2, vx0 - 2)
            vx1 = min(w - 3, vx1 + 2)
        return (vx0, vx1) if vx0 <= vx1 else None
    if py == 66:
        vis_bot = 46.0 * min(1.0, rug_span)
        vx0 = max(2, int(round(cx - vis_bot)))
        vx1 = min(w - 3, int(round(cx + vis_bot)))
        return (vx0, vx1) if vx0 <= vx1 else None
    return None


def _compose_subrow(
    py: int,
    w: int,
    min_py: int,
    rug_span: float,
    lights_on: bool,
    warm_p: float,
    radius: float,
    dark_nr: list[RGB],
    dark_rg: list[RGB],
    lit_nr: list[RGB],
    lit_rg: list[RGB],
    fallback: list[RGB],
) -> list[RGB]:
    """Compose one sub-pixel row with vertical wipe, carpet unroll, and radial hearth wash."""
    if py < min_py:
        return fallback[:]

    if rug_span <= 0.02:
        dark_row, lit_row = dark_nr, lit_nr
    elif rug_span >= 1.0:
        dark_row, lit_row = dark_rg, lit_rg
    else:
        bounds = _rug_row_bounds(py, w, rug_span)
        if bounds is None:
            dark_row, lit_row = dark_nr, lit_nr
        else:
            vx0, vx1 = bounds
            dark_row = dark_nr[:vx0] + dark_rg[vx0 : vx1 + 1] + dark_nr[vx1 + 1 :]
            if lights_on and warm_p > 0.0:
                lit_row = lit_nr[:vx0] + lit_rg[vx0 : vx1 + 1] + lit_nr[vx1 + 1 :]
            else:
                lit_row = dark_row

    if not lights_on or warm_p <= 0.0:
        return dark_row[:]
    if warm_p >= 1.0:
        return lit_row[:]
    if abs((py & ~1) - 40) > radius + 2.5:
        return dark_row[:]
    return [lit_row[x] if is_warm_lit(x, py, True, warm_p) else dark_row[x] for x in range(w)]


def _blend_row(row_a: list[RGB], row_b: list[RGB], w256: int) -> list[RGB]:
    """Blend two cached RGB rows using integer weight 0..256."""
    inv = 256 - w256
    return [
        (
            (a[0] * inv + b[0] * w256) >> 8,
            (a[1] * inv + b[1] * w256) >> 8,
            (a[2] * inv + b[2] * w256) >> 8,
        )
        for a, b in zip(row_a, row_b)
    ]


def _draw_settled_room(
    canvas: Canvas,
    t: float,
    active_mode: str,
    lights_on: bool,
    wp: float,
    ep: float,
    win_p: float,
) -> None:
    """Fast-path render once vertical reveal and hearth ignition have reached full bounds."""
    w, h = canvas.width, canvas.height
    if wp >= 1.0 and lights_on and 0.0 < ep < 1.0:
        fire_t, fire_b = _get_room_buffers(w, h, light_mode="fire", include_rug=True, default_bg=canvas.default_bg)
        full_t, full_b = _get_room_buffers(w, h, light_mode="full", include_rug=True, default_bg=canvas.default_bg)
        u_el = ep * ep * (3.0 - 2.0 * ep)
        w256 = max(0, min(256, int(round(u_el * 256.0))))
        canvas.load_subpixel_frame(
            [_blend_row(fa, fb, w256) for fa, fb in zip(fire_t, full_t)],
            [_blend_row(fa, fb, w256) for fa, fb in zip(fire_b, full_b)],
        )
        _draw_window_moonbeam(canvas, w, lights_on=(ep >= 0.5), min_py=0, win_p=win_p)
        _draw_hearth_floor_reflection(canvas, t, warm_p=wp, min_py=0)
        return

    top_buf, bot_buf = _get_room_buffers(w, h, light_mode=active_mode, include_rug=True, default_bg=canvas.default_bg)
    canvas.load_subpixel_frame(top_buf, bot_buf)
    _draw_window_moonbeam(canvas, w, lights_on=(active_mode == "full"), min_py=0, win_p=win_p)
    if active_mode != "dark":
        _draw_hearth_floor_reflection(canvas, t, warm_p=wp, min_py=0)


def draw_room_structure(
    canvas: Canvas,
    t: float,
    progress: float = 1.0,
    lights_on: bool = True,
    warm_p: float = 1.0,
    fire_lit: bool = True,
    win_p: float = 1.0,
    electric_p: float = 1.0,
) -> None:
    """Render room walls, moldings, floorboards, carpet, moonbeams, and floor firelight."""
    w, h = canvas.width, canvas.height
    p = max(0.0, min(1.0, progress))
    wp = max(0.0, min(1.0, warm_p)) if (lights_on or fire_lit) else 0.0
    ep = max(0.0, min(1.0, electric_p)) if lights_on else 0.0
    lit_mode = "full" if (lights_on and ep >= 1.0) else ("fire" if (fire_lit or lights_on) else "dark")
    active_mode = lit_mode if wp > 0.0 else "dark"

    if p >= 1.0 and (wp <= 0.0 or wp >= 1.0):
        _draw_settled_room(canvas, t, active_mode, lights_on, wp, ep, win_p)
        return

    e = 1.0 - (1.0 - p) ** 2
    min_py = 0 if p >= 1.0 else max(0, int(round((1.0 - e) * ((h - 1) * 2))))
    rug_span = 1.0 if p >= 1.0 else 1.0 - (1.0 - max(0.0, min(1.0, (p - 0.18) / 0.78))) ** 2

    dark_nr_t, dark_nr_b, dark_rg_t, dark_rg_b = _get_rug_pair(w, h, "dark", rug_span, canvas.default_bg)
    if wp > 0.0 and lit_mode != "dark":
        lit_nr_t, lit_nr_b, lit_rg_t, lit_rg_b = _get_rug_pair(w, h, lit_mode, rug_span, canvas.default_bg)
    else:
        lit_nr_t, lit_nr_b, lit_rg_t, lit_rg_b = dark_nr_t, dark_nr_b, dark_rg_t, dark_rg_b

    u = wp * wp * (3.0 - 2.0 * wp) if 0.0 < wp < 1.0 else 0.0
    radius = u * 98.0 if 0.0 < wp < 1.0 else 0.0
    out_top: list[list[RGB]] = []
    out_bot: list[list[RGB]] = []
    for y in range(h):
        py_t = y * 2
        py_b = py_t + 1
        if py_b < min_py:
            out_top.append(canvas._top_px[y][:])
            out_bot.append(canvas._bot_px[y][:])
            continue
        out_top.append(
            _compose_subrow(
                py_t, w, min_py, rug_span, (lit_mode != "dark"), wp, radius,
                dark_nr_t[y], dark_rg_t[y], lit_nr_t[y], lit_rg_t[y], canvas._top_px[y],
            )
        )
        out_bot.append(
            _compose_subrow(
                py_b, w, min_py, rug_span, (lit_mode != "dark"), wp, radius,
                dark_nr_b[y], dark_rg_b[y], lit_nr_b[y], lit_rg_b[y], canvas._bot_px[y],
            )
        )
    canvas.load_subpixel_frame(out_top, out_bot)
    if win_p > 0.18:
        _draw_window_moonbeam(canvas, w, lights_on=(active_mode == "full"), min_py=min_py, win_p=win_p)
    if active_mode != "dark" and wp > 0.15:
        _draw_hearth_floor_reflection(canvas, t, warm_p=wp, min_py=min_py)


def _draw_hearth_floor_reflection(canvas: Canvas, t: float, warm_p: float, min_py: int) -> None:
    """Add quantized flickering hearth reflections onto floorboard bevels and grain."""
    raw = 0.50 + 0.35 * math.sin(t * 4.2) + 0.15 * math.sin(t * 7.3 + 0.8)
    pulse = round(max(0.0, min(1.0, raw)) * 3.0) / 3.0
    if pulse <= 0.0:
        return

    warm_col = lerp_rgb(FLOOR_WARM_GLOW, STAR_GLOW, 0.25)
    for py in range(max(min_py, 52), 66):
        if py in _FLOOR_SEAM_ROWS:
            continue
        is_bevel = py in _FLOOR_BEVEL_ROWS
        for x in range(4, 30):
            dist = math.hypot((x - 16.0) * 0.45, (py - 51.0) * 0.65)
            atten = max(0.0, 1.0 - dist / 9.2)
            if atten <= 0.05:
                continue
            if is_bevel:
                strength = 0.24
            elif math.sin(x * 0.55 + py * 2.1) > 0.25:
                strength = 0.13
            else:
                continue
            canvas.blend_px(x, py, warm_col, strength * atten * pulse * warm_p)


def _draw_window_moonbeam(
    canvas: Canvas,
    w: int,
    lights_on: bool,
    min_py: int,
    win_p: float = 1.0,
) -> None:
    """Project divided-pane silver moonlight shafts diagonally across the right wall and floor."""
    if win_p <= 0.18:
        return
    beam_t = 1.0 if win_p >= 1.0 else max(0.0, min(1.0, (win_p - 0.18) / 0.82))
    beam_e = 1.0 - (1.0 - beam_t) ** 2
    moon_tint = lerp_rgb(FLOOR_MOON_GLOW, RUG_CREAM, 0.20)
    base_alpha = (0.14 if not lights_on else 0.08) * beam_e

    for py in range(max(min_py, 35), 69):
        if py in _FLOOR_SEAM_ROWS or py in (42, 43, 50, 51) or 56 <= py <= 58:
            continue
        shift = (py - 34.0) * 0.34
        bx0_full = max(76, int(round(86.0 - shift)))
        bx1_full = min(w - 2, int(round(111.0 - shift * 0.85)))
        mullion_x = int(round(98.0 - shift * 0.92))
        bx0 = bx0_full if beam_e >= 1.0 else int(round(mullion_x - (mullion_x - bx0_full) * beam_e))
        bx1 = bx1_full if beam_e >= 1.0 else int(round(mullion_x + (bx1_full - mullion_x) * beam_e))

        depth_atten = max(0.28, 1.0 - max(0.0, py - 48.0) / 28.0)
        bevel_boost = 1.35 if py in _FLOOR_BEVEL_ROWS else 1.0
        for x in range(bx0, bx1 + 1):
            if abs(x - mullion_x) <= 0:
                continue
            edge_soft = 0.55 if (x in (bx0, bx1) or abs(x - mullion_x) == 1) else 1.0
            canvas.blend_px(x, py, moon_tint, base_alpha * depth_atten * bevel_boost * edge_soft)


def _render_plaster_wall(canvas: Canvas, w: int, has_electric: bool, has_fire: bool, ambient_dim: float) -> None:
    """Fill plaster wall rows py = 3..39 with quantized vertical lighting for atlas compaction."""
    flicker = _STATIC_FLICKER
    for py in range(3, 40):
        # Snap lighting samples to 2-row cell alignment (py >= 4) so walls compress into space quads.
        sample_py = py if py == 3 else (py & ~1)
        wall_t = (sample_py - 3) / 36.0
        base_wall = scale_rgb(lerp_rgb(WALL_TOP_BG, WALL_BG, min(1.0, wall_t)), ambient_dim)
        for x in range(w):
            d_fire = math.hypot((x - 16) * 0.45, (sample_py - 36) * 0.55)
            fire_glow = max(0.0, 1.0 - d_fire / (26.0 if has_electric else 22.0)) * (0.60 if has_fire else 0.12) * flicker
            d_tree = math.hypot((x - 58) * 0.46, (sample_py - 25) * 0.58)
            tree_glow = max(0.0, 1.0 - d_tree / 26.0) * (0.52 if has_electric else 0.0)
            d_moon = math.hypot((x - 98) * 0.52, (sample_py - 18) * 0.55)
            moon_glow = max(0.0, 1.0 - d_moon / 24.0) * (0.38 if not has_electric else 0.18)

            col = lerp_rgb(base_wall, WALL_WARM_GLOW, fire_glow)
            col = lerp_rgb(col, WALL_TREE_GLOW, tree_glow)
            col = lerp_rgb(col, WALL_MOON_GLOW, moon_glow)
            if py == 3:
                col = lerp_rgb(col, SHADOW_PLUM, 0.48)
            canvas.set_px(x, py, col)


def _render_wainscot(canvas: Canvas, w: int, has_electric: bool, has_fire: bool, ambient_dim: float) -> None:
    """Render chair rail, recessed wood panels, and baseboard trim for py = 40..51."""
    flicker = _STATIC_FLICKER
    fire_span = 24.0 if has_electric else 18.0
    panel_fire_span = 25.0 if has_electric else 19.0

    for py in range(40, BASEBOARD_Y * 2):
        for x in range(w):
            if py in (40, 41, 42):
                warm = max(
                    max(0.0, 1.0 - abs(x - 16) * 0.45 / fire_span) * (0.54 if has_fire else 0.10) * flicker,
                    max(0.0, 1.0 - abs(x - 58) * 0.45 / 24.0) * (0.42 if has_electric else 0.0),
                )
                base = scale_rgb(WAINSCOT_TRIM if py == 40 else (WAINSCOT if py == 41 else SHADOW_PLUM), ambient_dim)
                canvas.set_px(x, py, lerp_rgb(base, FLOOR_WARM_GLOW, warm * 0.48))
            elif py < 50:
                warm = max(
                    max(0.0, 1.0 - math.hypot((x - 16) * 0.45, (py - 45) * 0.55) / panel_fire_span)
                    * (0.56 if has_fire else 0.10)
                    * flicker,
                    max(0.0, 1.0 - math.hypot((x - 58) * 0.45, (py - 45) * 0.55) / 24.0)
                    * (0.40 if has_electric else 0.0),
                )
                mod = x % 14
                if mod in (0, 1):
                    base = WAINSCOT
                elif py == 43 or mod == 2:
                    base = scale_rgb(WAINSCOT_RECESS, 0.7)
                elif py == 49 or mod == 13:
                    base = scale_rgb(WAINSCOT, 0.88)
                else:
                    base = WAINSCOT_RECESS
                canvas.set_px(x, py, lerp_rgb(scale_rgb(base, ambient_dim), WALL_WARM_GLOW, warm * 0.65))
            else:
                warm = max(0.0, 1.0 - abs(x - 16) * 0.45 / fire_span) * (0.48 if has_fire else 0.08) * flicker
                base = scale_rgb(BASEBOARD if py == 50 else scale_rgb(BASEBOARD, 0.68), ambient_dim)
                canvas.set_px(x, py, lerp_rgb(base, FLOOR_WARM_GLOW, warm * 0.48))


def _render_room_pixels(
    canvas: Canvas,
    w: int,
    h: int,
    include_rug: bool,
    light_mode: str,
) -> None:
    """Populate static ceiling beam, plaster wall, wainscot, floorboards, and Kilim rug."""
    has_electric = light_mode == "full"
    has_fire = light_mode != "dark"
    ambient_dim = 1.0 if has_electric else 0.72

    beam_dim = 1.0 if has_electric else 0.74
    for x in range(w):
        grain = (0.92 + 0.08 * math.sin(x * 0.35)) * beam_dim
        canvas.set_px(x, 0, scale_rgb(CEILING_BEAM_BG, grain))
        canvas.set_px(x, 1, scale_rgb(CEILING_BEAM, grain))
        canvas.set_px(x, 2, scale_rgb(CEILING_BEAM_BG, 0.82 * beam_dim))

    _render_plaster_wall(canvas, w, has_electric, has_fire, ambient_dim)
    _render_wainscot(canvas, w, has_electric, has_fire, ambient_dim)

    for step in range(4):
        for x_off in range(4 - step):
            canvas.set_px(x_off, 3 + step, CEILING_BEAM_BG)
            canvas.set_px(w - 1 - x_off, 3 + step, CEILING_BEAM_BG)

    _draw_floorboards(canvas, w=w, h=h, light_mode=light_mode)
    if include_rug:
        _draw_patterned_carpet(canvas, light_mode=light_mode)


def _draw_floorboards(canvas: Canvas, w: int, h: int, light_mode: str) -> None:
    """Render 1-point perspective walnut floorboards with seams, bevels, and grain."""
    center_x = w / 2.0
    vp_py = 26.0
    start_py = BASEBOARD_Y * 2
    end_py = (h - 1) * 2
    staggers = (0.0, 4.7, 1.9, 6.4, 3.2)
    plank_w = 9.5
    plank_tones = (0.85, 0.94, 1.03, 1.12)
    has_electric = light_mode == "full"
    has_fire = light_mode != "dark"
    floor_dim = 1.0 if has_electric else 0.68

    for py in range(start_py, end_py):
        depth = (py - start_py) / max(1, (h - 1) * 2 - start_py)
        base_wood = scale_rgb(lerp_rgb(FLOOR_BG_DARK, (62, 36, 28), depth), floor_dim)
        band_id = 0 if py <= 54 else (1 if py <= 57 else (2 if py <= 61 else (3 if py <= 65 else 4)))
        stagger = staggers[band_id]
        persp = (py - vp_py) / (start_py - vp_py)
        is_horiz_seam = py in _FLOOR_SEAM_ROWS
        is_bevel_hi = py in _FLOOR_BEVEL_ROWS
        near_horiz_seam = (py + 1) in _FLOOR_SEAM_ROWS or (py - 1) in _FLOOR_SEAM_ROWS
        seam_xs = {
            sx for k in range(-8, 9) if 0 <= (sx := int(round(center_x + (k * plank_w + stagger) * persp))) < w
        }

        for x in range(w):
            d_fire = math.hypot((x - 16) * 0.44, (py - 54) * 0.72)
            fire_glow = max(0.0, 1.0 - d_fire / (26.0 if has_electric else 21.0)) * (0.74 if has_fire else 0.14) * _STATIC_FLICKER
            tree_glow = max(0.0, 1.0 - math.hypot((x - 58) * 0.46, (py - 54) * 0.75) / 24.0) * (0.48 if has_electric else 0.0)
            moon = max(0.0, 1.0 - math.hypot((x - 98) * 0.50, (py - 56) * 0.70) / 20.0) * (0.36 if not has_electric else 0.12)

            plank_k = int(math.floor(((x - center_x) / persp - stagger) / plank_w))
            tone_idx = int(hash01(plank_k, band_id) * len(plank_tones)) % len(plank_tones)
            plank_col = lerp_rgb(scale_rgb(base_wood, plank_tones[tone_idx]), FLOOR_WARM_GLOW, min(0.84, fire_glow + tree_glow * 0.68))
            plank_col = lerp_rgb(plank_col, FLOOR_MOON_GLOW, moon)

            is_diag_seam = x in seam_xs
            is_right_of_seam = (x - 1) in seam_xs
            if py == start_py:
                col = lerp_rgb(plank_col, SHADOW_PLUM, 0.56)
            elif is_horiz_seam or is_diag_seam:
                col = scale_rgb(plank_col, 0.40 if (is_horiz_seam and (is_diag_seam or is_right_of_seam)) else 0.48)
            elif is_bevel_hi:
                col = lerp_rgb(plank_col, FLOOR_WOOD_LIGHT, 0.24 + fire_glow * 0.26)
            else:
                col = plank_col
                grain_wave = math.sin(x * 0.42 + plank_k * 2.3 + py * 4.1)
                if grain_wave > 0.74:
                    col = scale_rgb(col, 0.86)
                elif grain_wave < -0.82 and py >= 59:
                    col = lerp_rgb(col, FLOOR_WOOD_LIGHT, 0.14)
                if near_horiz_seam and is_right_of_seam:
                    col = scale_rgb(col, 0.82)
                if (py == 67 and x in (8, 9)) or (py == 68 and x in (104, 105)):
                    col = scale_rgb(col, 0.64)
            canvas.set_px(x, py, col)


def _kilim_weave_pixel(
    x: int,
    dy: int,
    py: int,
    py_top: int,
    py_bot: int,
    x0: int,
    x1: int,
    cx: float,
    persp_x: float,
) -> RGB:
    """Compute unlit Kilim rug pattern color at sub-pixel (x, py)."""
    wool_a: RGB = (198, 174, 144)
    wool_b: RGB = (182, 158, 128)
    kilim_red: RGB = (158, 46, 50)
    kilim_deep: RGB = (96, 28, 36)
    kilim_green: RGB = (36, 86, 58)
    kilim_gold: RGB = (196, 146, 78)

    edge_x = min(x - x0, x1 - x)
    is_outer = py in (py_top, py_bot) or edge_x == 0
    is_pine_band = (dy in (1, 11) or edge_x in (1, 2)) and not is_outer
    is_crimson_guard = (dy in (2, 10) or edge_x == 3) and not is_outer and not is_pine_band
    tile_u = int(round(abs(x - cx) / persp_x))

    if is_outer:
        return scale_rgb(kilim_deep, 0.78 if py == py_bot else 0.96)
    if is_pine_band:
        if dy in (1, 11) and edge_x >= 3:
            if tile_u % 4 == 0:
                return kilim_red if dy == 11 else wool_a
            return kilim_gold if (tile_u % 4 in (0, 1)) else kilim_green
        return kilim_gold if dy % 2 == 0 else kilim_green
    if is_crimson_guard:
        if (dy in (2, 10) and tile_u % 4 == 2 and edge_x >= 3) or (edge_x == 3 and dy % 3 == 0):
            return kilim_gold
        return kilim_red

    for wing_cx in (29.0, 85.0):
        md = abs(x - wing_cx) * 0.52 + abs(py - 59.5) * 1.05
        if md <= 1.20:
            return kilim_gold
        if md <= 2.35:
            return kilim_red
        if md <= 3.35:
            return kilim_green
    return wool_a if (((x // 2) + py) % 2 == 0) else wool_b


def _draw_patterned_carpet(canvas: Canvas, light_mode: str) -> None:
    """Render perspective-skewed oatmeal Kilim wool carpet with borders, medallions, and fringe."""
    has_electric = light_mode == "full"
    has_fire = light_mode != "dark"
    base_bright = 1.0 if has_electric else 0.52
    cx, py_top, py_bot = 57.0, 53, 65
    fringe_hi: RGB = (216, 198, 172)
    fringe_lo: RGB = (164, 144, 120)

    for py in range(py_top, py_bot + 1):
        dy = py - py_top
        t_y = dy / max(1, py_bot - py_top)
        half_w = 34.0 + t_y * 12.0
        x0, x1 = int(round(cx - half_w)), int(round(cx + half_w))
        persp_x = 1.0 + 0.35 * t_y

        for x in range(max(2, x0), min(canvas.width - 2, x1) + 1):
            col = _kilim_weave_pixel(x, dy, py, py_top, py_bot, x0, x1, cx, persp_x)
            d_fire = math.hypot((x - 18) * 0.44, (py - 57) * 0.72)
            fire_scatter = max(0.0, 1.0 - d_fire / (15.0 if has_electric else 13.5)) * (0.36 if has_fire else 0.08) * _STATIC_FLICKER
            tree_scatter = max(0.0, 1.0 - math.hypot((x - 58) * 0.44, (py - 56) * 0.75) / 17.0) * (0.28 if has_electric else 0.0)
            cool_tint = max(0.0, 1.0 - math.hypot((x - 92) * 0.45, (py - 59) * 0.75) / 18.0) * (0.38 if not has_electric else 0.14)

            col = lerp_rgb(col, FLOOR_WARM_GLOW, min(0.45, fire_scatter + tree_scatter) * 0.54)
            col = lerp_rgb(col, RUG_COOL, cool_tint * 0.50)
            px_bright = 1.0 if has_electric else (min(0.92, base_bright + fire_scatter * 1.15) if has_fire else base_bright)
            canvas.set_px(x, py, scale_rgb(col, px_bright))

        fringe_l_bright = 1.0 if has_electric else (0.86 if has_fire else base_bright)
        fringe_r_bright = 1.0 if has_electric else base_bright
        if py_top < py < py_bot:
            is_tuft = py % 2 == 1
            if x0 - 1 >= 2:
                canvas.set_px(x0 - 1, py, scale_rgb(fringe_hi if is_tuft else fringe_lo, 0.88 * fringe_l_bright))
            if is_tuft and x0 - 2 >= 2:
                canvas.set_px(x0 - 2, py, scale_rgb(fringe_lo, 0.75 * fringe_l_bright))
            if x1 + 1 < canvas.width - 2:
                canvas.set_px(x1 + 1, py, scale_rgb(fringe_hi if is_tuft else fringe_lo, 0.84 * fringe_r_bright))
            if is_tuft and x1 + 2 < canvas.width - 2:
                canvas.set_px(x1 + 2, py, scale_rgb(fringe_lo, 0.70 * fringe_r_bright))

    for x in range(max(2, int(round(cx - 46.0))), min(canvas.width - 2, int(round(cx + 46.0 + 1)))):
        canvas.blend_px(x, py_bot + 1, SHADOW_PLUM, 0.58)
