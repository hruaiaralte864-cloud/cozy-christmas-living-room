"""Pure sub-pixel 3D wrapped Christmas presents with overhanging lids, sculpted bows, and gift tags."""

from __future__ import annotations

from dataclasses import dataclass

from .canvas import Canvas
from .palette import FLOOR_WARM_GLOW, GIFT_THEMES, RGB, SHADOW_PLUM, STAR_BRIGHT, lerp_rgb, scale_rgb


@dataclass(frozen=True, slots=True)
class GiftBox:
    """Single 3D oblique wrapped present with lit/shadow planes, optional lid, tag, and sculpted bow."""

    x: int
    y_bottom: int
    w: int
    front_h: int
    depth: int
    theme_idx: int
    pattern: str  # "dots", "stripes", "checker", "solid"
    has_lid: bool = True
    has_tag: bool = False


# Varied-silhouette gift cluster resting on the rug beneath the tree (back-to-front painter's order)
DEFAULT_PRESENTS: tuple[GiftBox, ...] = (
    # Back row hugging the tree skirt (y_bottom = 27..28 -> py = 55..57)
    GiftBox(x=39, y_bottom=27, w=6, front_h=5, depth=2, theme_idx=4, pattern="dots", has_lid=True),
    GiftBox(x=46, y_bottom=27, w=8, front_h=6, depth=2, theme_idx=2, pattern="checker", has_lid=True, has_tag=True),
    GiftBox(x=62, y_bottom=27, w=8, front_h=6, depth=2, theme_idx=1, pattern="dots", has_lid=True),
    GiftBox(x=71, y_bottom=28, w=7, front_h=5, depth=2, theme_idx=3, pattern="stripes", has_lid=True),
    # Middle row overlapping cleanly in front (y_bottom = 30 -> py = 61)
    GiftBox(x=42, y_bottom=30, w=7, front_h=5, depth=2, theme_idx=5, pattern="stripes", has_lid=False),
    GiftBox(x=50, y_bottom=30, w=10, front_h=6, depth=2, theme_idx=0, pattern="solid", has_lid=True, has_tag=True),
    GiftBox(x=62, y_bottom=30, w=8, front_h=5, depth=2, theme_idx=6, pattern="checker", has_lid=True),
    # Foreground accents near front carpet border (y_bottom = 31 -> py = 63)
    GiftBox(x=46, y_bottom=31, w=6, front_h=4, depth=2, theme_idx=7, pattern="dots", has_lid=False),
    GiftBox(x=56, y_bottom=31, w=8, front_h=4, depth=2, theme_idx=3, pattern="checker", has_lid=True, has_tag=True),
)


def draw_presents(
    canvas: Canvas,
    progress: float = 1.0,
    lights_on: bool = True,
    fire_lit: bool = True,
) -> None:
    """Render 3D wrapped gift boxes dropping onto the carpet in back-to-front painter's order."""
    if progress <= 0.0:
        return

    base_bright = 1.0 if lights_on else 0.52
    total = len(DEFAULT_PRESENTS)

    if progress >= 1.0:
        for gift in DEFAULT_PRESENTS:
            _draw_single_gift(canvas, gift, base_bright, lights_on=lights_on, fire_lit=fire_lit)
        return

    drop_window = 0.42
    stride = (1.0 - drop_window) / max(1, total - 1)
    for idx, gift in enumerate(DEFAULT_PRESENTS):
        start = idx * stride
        if progress <= start:
            continue
        u = max(0.0, min(1.0, (progress - start) / drop_window))
        ease = 1.0 - (1.0 - u) ** 3
        drop_py = int(round(5.0 * (1.0 - ease)))
        shadow_scale = 0.25 + 0.75 * ease
        _draw_single_gift(
            canvas,
            gift,
            base_bright,
            lights_on=lights_on,
            fire_lit=fire_lit,
            drop_py=drop_py,
            shadow_scale=shadow_scale,
        )


def _draw_single_gift(
    canvas: Canvas,
    gift: GiftBox,
    brightness: float,
    lights_on: bool,
    fire_lit: bool = True,
    drop_py: int = 0,
    shadow_scale: float = 1.0,
) -> None:
    """Draw a 3D oblique wrapped gift box with top/side planes, lid shadow, ribbon, tag, and bow."""
    # Localized warm hearth luminance gradient on left boxes even when electric room lights are off
    if not lights_on and fire_lit and gift.x <= 54:
        brightness = min(0.86, brightness + 0.34 * max(0.0, 1.0 - (gift.x - 38) / 18.0))

    box_col, pat_col, rib_col = GIFT_THEMES[gift.theme_idx % len(GIFT_THEMES)]
    front_base = scale_rgb(box_col, brightness)
    top_base = lerp_rgb(scale_rgb(box_col, min(1.22, brightness * 1.14)), STAR_BRIGHT, 0.08 if lights_on else 0.0)
    side_base = lerp_rgb(scale_rgb(box_col, brightness * 0.62), SHADOW_PLUM, 0.32)
    pat_fg = scale_rgb(pat_col, brightness)

    rib_hi = lerp_rgb(rib_col, STAR_BRIGHT, 0.34 if lights_on else 0.08)
    rib_fg = scale_rgb(rib_col, brightness)
    rib_side = lerp_rgb(scale_rgb(rib_col, brightness * 0.68), SHADOW_PLUM, 0.28)

    # Warm hearth light bounce on left-side boxes whenever fire is burning
    if gift.x < 58 and (lights_on or fire_lit):
        warm_t = max(0.06, (0.20 if lights_on else 0.28) * (1.0 - (gift.x - 38) / 22.0))
        front_base = lerp_rgb(front_base, FLOOR_WARM_GLOW, warm_t)
        top_base = lerp_rgb(top_base, FLOOR_WARM_GLOW, warm_t)

    py_ground_bot = gift.y_bottom * 2 + 1
    py_front_top = (py_ground_bot - drop_py) - gift.front_h + 1
    rib_x = gift.x + gift.w // 2
    rib_py = py_front_top + gift.front_h // 2

    for dx in range(1, gift.w + 2):
        canvas.blend_px(gift.x + dx, py_ground_bot + 1, SHADOW_PLUM, 0.52 * shadow_scale)
    for d in range(1, gift.depth + 1):
        canvas.blend_px(gift.x + gift.w + d, py_ground_bot + 1 - d, SHADOW_PLUM, 0.44 * shadow_scale)
    for row in range(1, gift.front_h):
        canvas.blend_px(
            gift.x + gift.w + gift.depth,
            (py_ground_bot - drop_py) + row - gift.depth - gift.front_h + 1,
            SHADOW_PLUM,
            0.34 * shadow_scale,
        )

    _draw_gift_front(
        canvas, gift, py_front_top, rib_x, rib_py, front_base, pat_fg, rib_hi, rib_fg,
        lights_on, brightness, drop_py,
    )
    mid_d = (gift.depth + 1) // 2
    _draw_gift_top_and_side(canvas, gift, py_front_top, rib_x, mid_d, top_base, side_base, rib_hi, rib_fg, rib_side, brightness)

    if gift.has_tag and gift.w >= 8:
        tag_x = gift.x + gift.w // 2 - 2
        tag_py = py_front_top + (2 if gift.has_lid else 1)
        canvas.set_px(tag_x, tag_py, scale_rgb((244, 232, 206), brightness))
        canvas.set_px(tag_x + 1, tag_py, scale_rgb((186, 166, 138), brightness))

    _draw_sculpted_bow(
        canvas,
        bow_x=rib_x + mid_d,
        bow_py=py_front_top - mid_d,
        wide=gift.w >= 7,
        rib_hi=scale_rgb(rib_hi, brightness),
        rib_mid=rib_fg,
        rib_dark=rib_side,
    )


def _draw_gift_front(
    canvas: Canvas,
    gift: GiftBox,
    py_front_top: int,
    rib_x: int,
    rib_py: int,
    front_base: RGB,
    pat_fg: RGB,
    rib_hi: RGB,
    rib_fg: RGB,
    lights_on: bool,
    brightness: float,
    drop_py: int,
) -> None:
    """Render patterned box front, lid overhang crease, and ribbon."""
    for row in range(gift.front_h):
        py = py_front_top + row
        is_lid_top = gift.has_lid and row == 0
        is_under_lid = gift.has_lid and row == 1
        for col in range(gift.w):
            px = gift.x + col
            if px == rib_x or ((not gift.has_lid) and py == rib_py):
                col_rgb = scale_rgb(rib_hi, brightness) if row == 0 else (scale_rgb(rib_fg, 0.72) if is_under_lid else rib_fg)
            else:
                col_rgb = _pattern_px(gift.pattern, col, row, front_base, pat_fg)
                if is_lid_top:
                    col_rgb = lerp_rgb(scale_rgb(col_rgb, 1.08), STAR_BRIGHT, 0.06 if lights_on else 0.0)
                elif is_under_lid:
                    col_rgb = lerp_rgb(scale_rgb(col_rgb, 0.72), SHADOW_PLUM, 0.32)
                elif row == 0:
                    col_rgb = scale_rgb(col_rgb, 1.08)
                elif row == gift.front_h - 1:
                    col_rgb = lerp_rgb(scale_rgb(col_rgb, 0.88), SHADOW_PLUM, 0.16)
                if col == 0:
                    col_rgb = scale_rgb(col_rgb, 1.06)
                elif col == gift.w - 1:
                    col_rgb = lerp_rgb(scale_rgb(col_rgb, 0.90), SHADOW_PLUM, 0.14)
            if drop_py == 0 and gift.y_bottom <= 28 and row == 0 and 40 <= px <= 74:
                col_rgb = lerp_rgb(col_rgb, SHADOW_PLUM, 0.28)
            canvas.set_px(px, py, col_rgb)


def _draw_gift_top_and_side(
    canvas: Canvas,
    gift: GiftBox,
    py_front_top: int,
    rib_x: int,
    mid_d: int,
    top_base: RGB,
    side_base: RGB,
    rib_hi: RGB,
    rib_fg: RGB,
    rib_side: RGB,
    brightness: float,
) -> None:
    """Render oblique top lid plane and shaded right side face."""
    for d in range(1, gift.depth + 1):
        py = py_front_top - d
        for col in range(gift.w):
            px = gift.x + col + d
            if px == rib_x + d or d == mid_d:
                canvas.set_px(px, py, scale_rgb(rib_hi, brightness) if d == mid_d else rib_fg)
            else:
                canvas.set_px(px, py, scale_rgb(top_base, 1.04 if (col == 0 or d == gift.depth) else 0.96))

    for d in range(1, gift.depth + 1):
        px = gift.x + gift.w - 1 + d
        for row in range(gift.front_h):
            py = py_front_top + row - d
            if (not gift.has_lid) and row == gift.front_h // 2:
                col_rgb = rib_side
            elif gift.has_lid and row == 1:
                col_rgb = scale_rgb(side_base, 0.66)
            elif row == 0:
                col_rgb = scale_rgb(side_base, 1.12)
            else:
                col_rgb = side_base
            canvas.set_px(px, py, col_rgb)


def _draw_sculpted_bow(
    canvas: Canvas,
    bow_x: int,
    bow_py: int,
    wide: bool,
    rib_hi: RGB,
    rib_mid: RGB,
    rib_dark: RGB,
) -> None:
    """Render a 2-row satin bow with raised loops, bright center knot, and lid shadow."""
    if wide:
        # 5-col butterfly ribbon bow: raised flared loops + shadowed notch + bright center knot
        canvas.blend_px(bow_x - 2, bow_py, SHADOW_PLUM, 0.42)
        canvas.blend_px(bow_x + 2, bow_py, SHADOW_PLUM, 0.42)
        canvas.set_px(bow_x - 2, bow_py - 1, rib_hi)
        canvas.set_px(bow_x - 1, bow_py - 1, rib_mid)
        canvas.set_px(bow_x + 1, bow_py - 1, rib_mid)
        canvas.set_px(bow_x + 2, bow_py - 1, rib_dark)
        canvas.set_px(bow_x - 1, bow_py, rib_mid)
        canvas.set_px(bow_x, bow_py, rib_hi)
        canvas.set_px(bow_x + 1, bow_py, rib_dark)
    else:
        # 3-col crisp perched twin-wing bow
        canvas.set_px(bow_x - 1, bow_py - 1, rib_hi)
        canvas.set_px(bow_x + 1, bow_py - 1, rib_dark)
        canvas.set_px(bow_x, bow_py, rib_hi)
        canvas.set_px(bow_x - 1, bow_py, rib_mid)
        canvas.set_px(bow_x + 1, bow_py, rib_dark)


def _pattern_px(
    pattern: str,
    col: int,
    row: int,
    base: RGB,
    pat: RGB,
) -> RGB:
    """Return refined wrapping-paper pixel color for front box face."""
    if pattern == "dots" and col % 3 == 1 and row % 2 == 1:
        return lerp_rgb(base, pat, 0.72)
    if pattern == "stripes" and col % 2 == 0:
        return lerp_rgb(base, pat, 0.42)
    if pattern == "checker" and (col + row) % 2 == 0:
        return lerp_rgb(base, pat, 0.34)
    return base
