"""Pure sub-pixel painterly Christmas tree with sculpted 3D pine boughs, glossy baubles, and 5-point star."""

from __future__ import annotations

import math
import random

from .canvas import Canvas
from .palette import (
    FLOOR_MOON_GLOW,
    FLOOR_WARM_GLOW,
    LIGHT_COLORS,
    PINE_DARK,
    PINE_FROST,
    PINE_LIGHT,
    PINE_MID,
    RGB,
    RUG_OUTER,
    RUG_TRIM,
    SHADOW_PLUM,
    STAR_BRIGHT,
    STAR_GLOW,
    TINSEL_GOLD,
    TREE_BG,
    TRUNK_BROWN,
    hash01,
    lerp_rgb,
    scale_rgb,
)


class ChristmasTree:
    """Centerpiece evergreen tree with 5 cascading bough tiers, wrapped garlands, baubles, and lights."""

    # Predefined 5 cascading tier bounds: (py_start, py_end, half_w_start, half_w_end, lobes)
    _TIERS: tuple[tuple[int, int, int, int, int], ...] = (
        (8, 13, 1, 5, 1),    # Crown spire
        (14, 21, 4, 8, 2),   # Upper bough tier
        (22, 30, 7, 11, 3),  # Upper-mid bough tier (stays clear of x=29..45 bookcase)
        (31, 39, 10, 15, 4), # Lower-mid bough tier
        (40, 49, 13, 18, 5), # Wide sweeping base boughs
    )

    # Shaded 2x2 glass baubles: (dx_from_cx, py, kind_idx) where 0=ruby, 1=gold, 2=sapphire
    _BAUBLES: tuple[tuple[int, int, int], ...] = (
        (-3, 19, 0),
        (2, 20, 1),
        (-5, 27, 2),
        (1, 28, 0),
        (6, 26, 1),
        (-8, 36, 1),
        (-2, 37, 2),
        (5, 36, 0),
        (-11, 44, 0),
        (-4, 46, 1),
        (3, 45, 2),
        (11, 44, 0),
    )

    def __init__(self, cx: int = 58, top_y: int = 4, bottom_y: int = 24, seed: int = 2026) -> None:
        self.cx = cx
        self.top_y = top_y
        self.bottom_y = bottom_y
        self.top_py = top_y * 2            # py = 8
        self.bottom_py = bottom_y * 2 + 1  # py = 49
        self.rng = random.Random(seed)

        # Build per-row tier metadata: (py, half_w, tier_idx, t_v, is_tier_bottom)
        self.rows: list[tuple[int, int, int, float, bool]] = []
        for tier_idx, (p0, p1, w0, w1, _lobes) in enumerate(self._TIERS):
            span = max(1, p1 - p0)
            for py in range(p0, p1 + 1):
                if py < self.top_py or py > self.bottom_py:
                    continue
                t_v = (py - p0) / span
                # Drooping wingtips flare slightly outward near tier bottoms before tucking under
                wing_flare = 0.8 if (tier_idx >= 1 and t_v >= 0.72) else 0.0
                half_w = max(1, min(18, int(round(w0 + (w1 - w0) * (t_v ** 0.78) + wing_flare * 0.5))))
                if py <= self.top_py + 1:
                    half_w = 1
                self.rows.append((py, half_w, tier_idx, t_v, py == p1))

        # Place ~30 warm fairy string lights along curved branch arcs (avoiding bauble cores)
        bauble_cells = {(cx + bx + ox, bpy + oy) for bx, bpy, _ in self._BAUBLES for ox in (0, 1) for oy in (0, 1)}
        self.ornaments: list[tuple[int, int, int, float]] = []
        for idx, (py, half_w, _, t_v, _) in enumerate(self.rows):
            if py < 11 or idx % 4 != 1 or t_v > 0.88:
                continue
            step = 5 if half_w <= 10 else 6
            offset = (idx % 3)
            for dx in range(-half_w + 2 + offset, half_w - 1, step):
                ox = cx + dx
                opy = py + (1 if (abs(dx) % 3 == 1 and py < self.bottom_py) else 0)
                if (ox, opy) in bauble_cells or abs(ox - cx) > half_w - 1:
                    continue
                # Warm cozy balance: mostly creamy white & apricot gold with subtle ruby/ice sparkle
                palette_pick = (idx + abs(dx)) % 6
                color_idx = 0 if palette_pick in (0, 3) else (1 if palette_pick in (1, 4) else (2 if palette_pick == 2 else 4))
                phase = self.rng.uniform(0.0, math.tau)
                self.ornaments.append((ox, opy, color_idx, phase))

    def draw(
        self,
        canvas: Canvas,
        t: float,
        tree_progress: float = 1.0,
        decor_progress: float = 1.0,
        lights_on: bool = True,
        fire_lit: bool = True,
        electric_p: float = 1.0,
    ) -> None:
        """Draw trunk, skirt, 3D bough foliage, wrapped garlands, glossy baubles, lights, and star."""
        if tree_progress <= 0.0:
            return

        ep = 0.0 if not lights_on else max(0.0, min(1.0, electric_p))
        if ep < 1.0 and ep > 0.0:
            ep = ep * ep * (3.0 - 2.0 * ep)

        if tree_progress >= 0.04:
            self._draw_trunk_and_skirt(canvas, lights_on=lights_on, electric_mix=ep)

        e_tree = 1.0 - (1.0 - min(1.0, tree_progress)) ** 2
        visible_rows = max(1, int(round(len(self.rows) * e_tree)))
        for py, half_w, tier_idx, t_v, is_bottom in self.rows[-visible_rows:]:
            self._draw_pine_row(
                canvas,
                py,
                half_w,
                tier_idx,
                t_v,
                is_bottom,
                lights_on=lights_on,
                fire_lit=fire_lit,
                electric_mix=ep,
            )

        if decor_progress <= 0.05:
            return

        self._draw_garlands(canvas, decor_progress, lights_on=lights_on, electric_mix=ep)

        if decor_progress >= 0.22:
            self._draw_baubles(canvas, t, decor_progress, lights_on=lights_on, electric_mix=ep)

        if decor_progress >= 0.45:
            self._draw_fairy_lights(canvas, t, decor_progress, lights_on=lights_on)

        if decor_progress >= 0.78:
            star_t = min(1.0, (decor_progress - 0.78) / 0.22)
            self._draw_star_topper(canvas, t, lights_on=lights_on, settle_p=star_t)

    def _draw_trunk_and_skirt(
        self,
        canvas: Canvas,
        lights_on: bool,
        electric_mix: float = 1.0,
    ) -> None:
        """Draw the shaded bark trunk and pleated crimson/gold embroidered tree skirt."""
        cx = self.cx
        bright = 0.52 + 0.48 * electric_mix if lights_on else 0.52

        for py in range(52, 55):
            half = 11 + (py - 52)
            for dx in range(-half, half + 1):
                is_trim = abs(dx) >= half - 1 or py == 54
                fold = 0.82 if (dx % 4 == 0) else 1.0
                base = RUG_TRIM if is_trim else scale_rgb(RUG_OUTER, fold)
                if dx < -3 and lights_on and not is_trim:
                    base = lerp_rgb(base, FLOOR_WARM_GLOW, 0.22)
                canvas.set_px(cx + dx, py, scale_rgb(base, bright))
        for dx in range(-13, 14):
            canvas.blend_px(cx + dx, 55, SHADOW_PLUM, 0.48)

        for py in range(49, 53):
            for dx in (-2, -1, 0, 1, 2):
                bark = 1.08 if dx == -1 else (0.92 if dx == 0 else (0.64 if dx == 2 else 0.78))
                col = scale_rgb(TRUNK_BROWN, bright * bark)
                if py == 49:
                    col = lerp_rgb(col, SHADOW_PLUM, 0.45)
                canvas.set_px(cx + dx, py, col)

    def _pine_pixel_color(
        self,
        dx: int,
        abs_u: float,
        tier_idx: int,
        t_v: float,
        is_tier_bottom: bool,
        t_branch: float,
        lobe_val: float,
        noise: float,
        p_deep: RGB,
        p_dark: RGB,
        p_mid: RGB,
        p_light: RGB,
        p_crest: RGB,
    ) -> RGB:
        """Select tiered pine needle shade based on overhang and bough-lobe geometry."""
        if tier_idx >= 1 and 0.0 <= t_branch <= 0.15 and abs_u < 0.78:
            if abs(dx) <= 1 and tier_idx >= 2 and noise > 0.80:
                return scale_rgb(TRUNK_BROWN, 0.68)
            return p_deep if noise > 0.24 else p_dark
        if (is_tier_bottom or t_v >= 0.80) and lobe_val < 0.10 and abs_u < 0.90:
            return p_deep if noise < 0.50 else p_dark
        if t_branch <= 0.46 and lobe_val > 0.20:
            if t_branch <= 0.24 and lobe_val > 0.60 and noise > 0.42:
                return p_crest
            return p_light if noise > 0.30 else p_mid
        if lobe_val > -0.18:
            if is_tier_bottom and lobe_val > 0.42 and noise > 0.52:
                return p_light
            return p_mid if noise > 0.28 else p_dark
        return p_dark if noise > 0.35 else p_deep

    def _draw_pine_row(
        self,
        canvas: Canvas,
        py: int,
        half_w: int,
        tier_idx: int,
        t_v: float,
        is_tier_bottom: bool,
        lights_on: bool,
        fire_lit: bool = True,
        electric_mix: float = 1.0,
    ) -> None:
        """Render one horizontal row of overlapping evergreen pine boughs."""
        bright = (0.50 + 0.50 * electric_mix) if lights_on else 0.50
        p_deep, p_dark, p_mid, p_light = TREE_BG, PINE_DARK, PINE_MID, PINE_LIGHT
        p_crest = lerp_rgb(PINE_LIGHT, PINE_FROST, 0.42)
        p_warm = lerp_rgb(PINE_LIGHT, FLOOR_WARM_GLOW, 0.24)
        p_cool = lerp_rgb(PINE_MID, FLOOR_MOON_GLOW, 0.22 if not lights_on else 0.14)

        sub_band = int((t_v + 0.12) * 3.0)
        paw_span = 3.0 + tier_idx * 0.18
        for dx in range(-half_w, half_w + 1):
            if abs(dx) == half_w and half_w >= 4 and not is_tier_bottom and (py + tier_idx) % 2 == 1:
                continue
            px = self.cx + dx
            abs_u = abs(dx / max(1, half_w))
            t_branch = t_v - 0.26 * (abs_u ** 1.35)
            stagger_shift = (sub_band % 2) * (paw_span * 0.52) + (abs(dx) * 0.25 - t_v * 1.4)
            lobe_val = math.cos(((dx + stagger_shift + tier_idx * 1.15) / paw_span) * math.pi)
            col = self._pine_pixel_color(
                dx, abs_u, tier_idx, t_v, is_tier_bottom, t_branch, lobe_val,
                hash01(px, py), p_deep, p_dark, p_mid, p_light, p_crest,
            )

            px_bright = bright
            if (lights_on or fire_lit) and dx < -2 and abs_u > (0.62 if electric_mix >= 0.65 else 0.54) and col in (p_mid, p_light, p_crest):
                if lights_on and electric_mix >= 0.65:
                    col = p_warm
                elif py >= 16:
                    fire_rim = lerp_rgb(p_light, FLOOR_WARM_GLOW, 0.34)
                    col = lerp_rgb(fire_rim, p_warm, electric_mix) if lights_on else fire_rim
                    px_bright = max(bright, 0.84)
            elif dx > 2 and abs_u > 0.74 and col in (p_mid, p_light):
                col = p_cool

            canvas.set_px(px, py, scale_rgb(col, px_bright))

    def _draw_garlands(
        self,
        canvas: Canvas,
        decor_progress: float,
        lights_on: bool,
        electric_mix: float = 1.0,
    ) -> None:
        """Draw alternating golden bead garlands & crimson velvet ribbons wrapping 3D boughs."""
        # (py_anchor_left, py_anchor_right, sag_px, span_half, is_ribbon, tuck_xs)
        swags: tuple[tuple[int, int, float, int, bool, tuple[int, ...]], ...] = (
            (15, 17, 2.3, 5, False, ()),
            (22, 24, 3.0, 8, True, (-3, 4)),
            (30, 32, 3.6, 11, False, (-5, 5)),
            (39, 41, 4.2, 14, True, (-7, 0, 7)),
        )
        gp = min(1.0, decor_progress / 0.58)
        bright = (0.44 + 0.56 * electric_mix) if lights_on else 0.44

        # Wrap garlands left-to-right bottom-to-top matching upward tree growth
        for idx, (py_l, py_r, sag, span_half, is_ribbon, tuck_xs) in enumerate(swags[::-1]):
            local_p = max(0.0, min(1.0, (gp - idx * 0.19) / 0.43))
            if local_p <= 0.0:
                continue
            max_dx = (
                span_half
                if local_p >= 1.0
                else -span_half + int(round(2 * span_half * (1.0 - (1.0 - local_p) ** 2)))
            )
            for dx in range(-span_half, max_dx + 1):
                if dx in tuck_xs:
                    # Let a foreground pine tip tuck cleanly in front of the garland
                    continue
                u = dx / max(1, span_half)
                base_y = py_l + (py_r - py_l) * (0.5 * (u + 1.0))
                py = int(round(base_y + sag * (1.0 - u * u)))
                px = self.cx + dx

                # Drop 1-px shadow directly underneath onto pine needles
                canvas.blend_px(px, py + 1, TREE_BG, 0.65)

                if is_ribbon:
                    col = RUG_TRIM if abs(dx) % 3 == 0 else RUG_OUTER
                    if abs(u) < 0.35 and lights_on and abs(dx) % 2 == 0:
                        col = lerp_rgb(col, STAR_GLOW, 0.30)
                else:
                    # Beaded pearl garland catching specular highlight toward center
                    if abs(u) < 0.42 and dx % 2 == 0 and lights_on:
                        col = STAR_BRIGHT
                    elif dx % 2 == 0:
                        col = TINSEL_GOLD
                    else:
                        col = scale_rgb(TINSEL_GOLD, 0.70)
                canvas.set_px(px, py, scale_rgb(col, bright))

    def _draw_baubles(
        self,
        canvas: Canvas,
        t: float,
        decor_progress: float,
        lights_on: bool,
        electric_mix: float = 1.0,
    ) -> None:
        """Render shaded 2x2 glossy glass ornaments with specular highlight & shadow belly."""
        # (top_left_specular, main_midtone, bottom_right_shadow)
        kinds: tuple[tuple[RGB, RGB, RGB], ...] = (
            ((255, 214, 210), (196, 42, 54), (96, 18, 28)),   # Ruby red
            ((255, 248, 212), (232, 178, 72), (132, 82, 26)), # Champagne gold
            ((232, 246, 255), (82, 154, 214), (36, 74, 124)), # Frosted cobalt-ice
        )
        count = (
            len(self._BAUBLES)
            if decor_progress >= 0.72
            else int(round(len(self._BAUBLES) * max(0.0, min(1.0, (decor_progress - 0.22) / 0.50))))
        )
        dim = (0.42 + 0.58 * electric_mix) if lights_on else 0.42

        for idx, (dx, py, kind_idx) in enumerate(self._BAUBLES[::-1][:count]):
            bx = self.cx + dx
            spec, mid, shade = kinds[kind_idx]
            sparkle = lights_on and int(t * 2.2 + idx * 1.7) % 5 == 0
            tl = STAR_BRIGHT if sparkle else (spec if lights_on else scale_rgb(mid, dim))
            canvas.set_px(bx, py, tl)
            canvas.set_px(bx + 1, py, scale_rgb(mid, dim))
            canvas.set_px(bx, py + 1, scale_rgb(mid, dim))
            canvas.set_px(bx + 1, py + 1, scale_rgb(shade, dim))

    def _draw_fairy_lights(self, canvas: Canvas, t: float, decor_progress: float, lights_on: bool) -> None:
        """Render discrete-step twinkling micro fairy lights with soft warm needle reflection."""
        orn_count = int(len(self.ornaments) * min(1.0, (decor_progress - 0.45) / 0.45))
        for ox, opy, color_idx, phase in self.ornaments[::-1][:orn_count]:
            base_col = LIGHT_COLORS[color_idx]
            if lights_on:
                raw_twinkle = 0.50 + 0.50 * math.sin(t * 3.6 + phase)
                twinkle = 0.50 if raw_twinkle < 0.35 else (0.78 if raw_twinkle < 0.72 else 1.0)
                if twinkle >= 0.78:
                    bloom_col = lerp_rgb(base_col, STAR_GLOW, 0.38)
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        canvas.blend_px(ox + dx, opy + dy, bloom_col, 0.26 * twinkle)
                core = STAR_BRIGHT if twinkle == 1.0 else lerp_rgb(base_col, STAR_BRIGHT, 0.35 * twinkle)
                canvas.set_px(ox, opy, core)
            else:
                canvas.set_px(ox, opy, scale_rgb(base_col, 0.24))

    def _draw_star_topper(
        self,
        canvas: Canvas,
        t: float,
        lights_on: bool,
        settle_p: float = 1.0,
    ) -> None:
        """Render a detailed faceted 5-point gold Christmas star topper with warm aura."""
        cx = self.cx
        sp = max(0.0, min(1.0, settle_p))
        top_py = 3  # mounts cleanly onto pine spire at py = 8 without touching ceiling wire at py = 2

        pulse = 0.72 if not lights_on else (0.84 if math.sin(t * 3.8) < 0.0 else 1.0)
        palette = {
            "C": STAR_BRIGHT if lights_on else scale_rgb(TINSEL_GOLD, 0.54),
            "W": lerp_rgb(STAR_BRIGHT, STAR_GLOW, 0.32) if lights_on else scale_rgb(TINSEL_GOLD, 0.48),
            "H": scale_rgb(STAR_GLOW, 0.96 * pulse) if lights_on else scale_rgb(TINSEL_GOLD, 0.42),
            "G": scale_rgb(TINSEL_GOLD, 0.86 * pulse) if lights_on else scale_rgb(TINSEL_GOLD, 0.36),
            "D": scale_rgb(TINSEL_GOLD, 0.56) if lights_on else scale_rgb(TINSEL_GOLD, 0.28),
            "b": (122, 82, 34) if lights_on else (72, 50, 26),
        }
        star_sprite = (
            "....H....",  # py = 3 crisp upper point tip
            "...HWG...",  # py = 4 faceted top spire
            "HWWWCGGGD",  # py = 5 wide 9-col outstretched star arms with center highlight
            "..HWCGG..",  # py = 6 beveled waist with bright jewel core at (cx, 6)
            ".HWGbGGD.",  # py = 7 sculpted lower wings flanking central brass socket
            ".G..b..D.",  # py = 8 sharp lower star tips & ferrule mount on pine spire
        )

        if lights_on and sp >= 0.25:
            aura_scale = min(1.0, (sp - 0.25) / 0.75) * pulse
            # Soft warm halo behind star facets (kept cleanly below ceiling wire at py = 2)
            for dy in range(0, 7):
                for dx in range(-5, 6):
                    dist = math.hypot(dx * 0.72, (dy - 2.2) * 0.90)
                    if dist <= 3.6:
                        canvas.blend_px(cx + dx, top_py + dy, STAR_GLOW, (0.34 - dist * 0.08) * aura_scale)
            # Subtle 1-px twinkle glints nestled in the star's diagonal corner pockets
            if sp >= 0.65:
                glint = lerp_rgb(STAR_GLOW, STAR_BRIGHT, 0.55)
                glint_a = min(1.0, (sp - 0.65) / 0.35) * 0.36
                for gx, gy in ((-2, 4), (2, 4), (-3, 6), (3, 6)):
                    canvas.blend_px(cx + gx, gy, glint, glint_a)

        max_dx = 1 if sp < 0.35 else (2 if sp < 0.72 else 4)
        min_dy = 4 if sp < 0.30 else (2 if sp < 0.68 else 0)
        for dy, row in enumerate(star_sprite):
            if dy < min_dy:
                continue
            py = top_py + dy
            for dx, ch in enumerate(row):
                if ch != "." and abs(dx - 4) <= max_dx:
                    canvas.set_px(cx - 4 + dx, py, palette[ch])
