"""Painterly 24-bit TrueColor RGB palette and color interpolation utilities."""

from __future__ import annotations

RGB = tuple[int, int, int]

# Deep atmospheric shadows & warm-vs-cool ambient lighting
SHADOW_PLUM: RGB = (18, 15, 24)
WALL_BG: RGB = (30, 24, 34)
WALL_TOP_BG: RGB = (22, 24, 38)
WALL_WARM_GLOW: RGB = (176, 102, 72)
WALL_TREE_GLOW: RGB = (198, 118, 78)
WALL_MOON_GLOW: RGB = (52, 74, 114)

WAINSCOT: RGB = (74, 48, 40)
WAINSCOT_RECESS: RGB = (36, 24, 26)
WAINSCOT_TRIM: RGB = (122, 78, 58)
BASEBOARD: RGB = (92, 58, 44)
CEILING_BEAM: RGB = (72, 46, 38)
CEILING_BEAM_BG: RGB = (36, 24, 26)

# Dark walnut floorboards & woven wool carpet
FLOOR_BG_DARK: RGB = (34, 20, 20)
FLOOR_WOOD_LIGHT: RGB = (118, 68, 44)
FLOOR_WARM_GLOW: RGB = (218, 134, 78)
FLOOR_MOON_GLOW: RGB = (76, 104, 152)

RUG_OUTER: RGB = (126, 46, 52)
RUG_CREAM: RGB = (196, 154, 128)
RUG_COOL: RGB = (64, 72, 104)
RUG_TRIM: RGB = (184, 132, 92)

# Tree & foliage colors (deep velvety pine + warm golden light bloom)
PINE_DARK: RGB = (18, 42, 30)
PINE_MID: RGB = (34, 78, 48)
PINE_LIGHT: RGB = (58, 118, 66)
PINE_FROST: RGB = (138, 178, 134)
TREE_BG: RGB = (14, 28, 22)
TRUNK_BROWN: RGB = (82, 48, 32)
TINSEL_GOLD: RGB = (232, 182, 92)

STAR_BRIGHT: RGB = (255, 248, 212)
STAR_GLOW: RGB = (255, 196, 92)

# Warm painterly fairy light & ornament colors
LIGHT_COLORS: tuple[RGB, ...] = (
    (255, 242, 188),  # Creamy warm white
    (255, 176, 78),   # Apricot gold
    (244, 88, 78),    # Warm coral red
    (128, 224, 184),  # Soft mint glow
    (132, 194, 248),  # Soft ice blue
    (248, 134, 168),  # Dusty rose
)

# Fireplace & warm accents
BRICK_DARK: RGB = (84, 34, 32)
BRICK_MID: RGB = (114, 46, 38)
BRICK_LIGHT: RGB = (146, 62, 46)
BRICK_MORTAR: RGB = (34, 18, 20)
BRICK_WARM_GLOW: RGB = (224, 114, 58)
MANTEL_WOOD: RGB = (112, 66, 44)
MANTEL_BG: RGB = (52, 30, 24)
HEARTH_BG: RGB = (18, 10, 12)
LOG_WOOD: RGB = (68, 38, 26)

FIRE_PALETTE: tuple[RGB, ...] = (
    (124, 24, 18),
    (184, 54, 22),
    (232, 102, 32),
    (252, 164, 62),
    (255, 218, 116),
    (255, 248, 204),
)

STOCKING_RED: RGB = (188, 46, 54)
STOCKING_GREEN: RGB = (46, 128, 70)
CUFF_WHITE: RGB = (232, 224, 216)

# Window & night snow
NIGHT_SKY_TOP: RGB = (12, 18, 40)
NIGHT_SKY_BOT: RGB = (32, 46, 82)
WINDOW_FRAME: RGB = (104, 66, 46)
MOON_YELLOW: RGB = (252, 240, 184)
STAR_WHITE: RGB = (214, 226, 255)
SNOW_WHITE: RGB = (232, 240, 252)
SNOW_SOFT: RGB = (146, 172, 214)
HILL_DARK: RGB = (36, 50, 82)
HILL_SNOW: RGB = (166, 188, 224)

# Furniture, curtains & woodwork
CURTAIN_MAIN: RGB = (104, 34, 42)
CURTAIN_LIGHT: RGB = (148, 52, 56)
CURTAIN_SHADOW: RGB = (56, 20, 28)
CHAIR_FABRIC: RGB = (126, 42, 48)
CHAIR_SHADOW: RGB = (64, 22, 30)
CHAIR_CUSHION: RGB = (164, 62, 64)
TABLE_WOOD: RGB = (102, 64, 42)

# Gift wrap palettes: (box_color, pattern_color, ribbon_color)
GIFT_THEMES: tuple[tuple[RGB, RGB, RGB], ...] = (
    ((178, 46, 52), (218, 86, 82), (242, 204, 108)),   # Crimson + Cream Gold
    ((48, 92, 158), (88, 138, 198), (228, 232, 242)),  # Slate Blue + Ivory
    ((42, 118, 68), (78, 158, 96), (216, 62, 68)),     # Forest + Red
    ((198, 144, 54), (232, 186, 98), (168, 42, 48)),   # Ochre Gold + Crimson
    ((126, 58, 146), (166, 98, 186), (238, 220, 138)), # Plum + Champagne
    ((192, 88, 52), (226, 132, 86), (236, 232, 226)),  # Terracotta + Cream
    ((46, 128, 138), (94, 172, 182), (242, 192, 86)),  # Teal + Gold
    ((162, 54, 96), (206, 98, 138), (234, 230, 224)),  # Berry + Cream
)

UI_MUTED: RGB = (148, 156, 172)
UI_ACCENT: RGB = (255, 216, 102)


def lerp_rgb(c1: RGB, c2: RGB, t: float) -> RGB:
    """Linearly interpolate between two RGB colors with t clamped to [0, 1]."""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def scale_rgb(c: RGB, factor: float) -> RGB:
    """Scale brightness of an RGB color safely within [0, 255]."""
    return (
        max(0, min(255, int(c[0] * factor))),
        max(0, min(255, int(c[1] * factor))),
        max(0, min(255, int(c[2] * factor))),
    )


def hash01(x: int, y: int) -> float:
    """Fast deterministic [0, 1] pseudo-random float for textures and particle seeds."""
    n = (x * 374761393 + y * 668265263) ^ 0x5BF03635
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0
