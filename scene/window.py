"""Frosted night window showing 3D crescent moon, drifting clouds, alpine pines, and realistic snow."""

from __future__ import annotations

import math
import random

from .canvas import Canvas
from .palette import (
    FLOOR_WARM_GLOW,
    HILL_DARK,
    HILL_SNOW,
    MOON_YELLOW,
    NIGHT_SKY_BOT,
    NIGHT_SKY_TOP,
    PINE_DARK,
    SHADOW_PLUM,
    SNOW_SOFT,
    SNOW_WHITE,
    STAR_WHITE,
    TABLE_WOOD,
    WALL_TREE_GLOW,
    WINDOW_FRAME,
    hash01,
    lerp_rgb,
    scale_rgb,
)


class NightWindow:
    """Wooden-framed living room window with alpine winter landscape and realistic snowfall."""

    def __init__(self, x: int = 85, y: int = 4, w: int = 27, h: int = 13, seed: int = 99) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.rng = random.Random(seed)

        self.glass_w = w - 2              # 25 cols (x = 86..110)
        self.glass_px_h = (h - 2) * 2     # 22 sub-pixels (py = 10..31)

        # 3-depth parallax flakes: [x, py, speed_y, wind_scale, flutter_phase, flutter_freq, layer]
        # layer: 0 = far mist, 1 = mid drift, 2 = near bright
        self.flakes: list[list[float | int]] = []
        for idx in range(40):
            layer = 0 if idx < 18 else (1 if idx < 32 else 2)
            if layer == 0:
                speed = self.rng.uniform(0.08, 0.16)
                wind_scale = self.rng.uniform(0.45, 0.70)
            elif layer == 1:
                speed = self.rng.uniform(0.18, 0.30)
                wind_scale = self.rng.uniform(0.80, 1.05)
            else:
                speed = self.rng.uniform(0.32, 0.48)
                wind_scale = self.rng.uniform(1.10, 1.40)

            self.flakes.append([
                self.rng.uniform(0.0, float(self.glass_w)),
                self.rng.uniform(0.0, float(self.glass_px_h - 2)),
                speed,
                wind_scale,
                self.rng.uniform(0.0, math.tau),
                self.rng.uniform(1.1, 2.6),
                layer,
            ])

        # Fixed starfield across upper sky (gx, dy, phase, base_brightness)
        self.stars: list[tuple[int, int, float, float]] = [
            (2, 1, 0.2, 0.85),
            (5, 4, 1.4, 0.65),
            (8, 2, 2.7, 0.95),
            (11, 5, 3.5, 0.60),
            (3, 7, 4.1, 0.75),
            (14, 1, 5.0, 0.80),
            (15, 7, 2.0, 0.70),
            (23, 8, 0.9, 0.65),
            (10, 1, 4.8, 0.55),
        ]

    def draw(
        self,
        canvas: Canvas,
        t: float,
        progress: float = 1.0,
        lights_on: bool = True,
        reflect_p: float = 1.0,
    ) -> None:
        """Render twilight sky, 3D crescent moon, clouds, mountains, pines, snowfall, and frame."""
        if progress <= 0.02:
            return

        x0, y0 = self.x, self.y
        gx0 = x0 + 1
        gy0_py = (y0 + 1) * 2
        frame_p = min(1.0, progress / 0.34)
        frame_min_py = 0 if progress >= 0.34 else ((y0 + self.h - 1) * 2 + 3) - int(
            round(28.0 * (1.0 - (1.0 - frame_p) ** 2))
        )
        show_glass, vis_gx0, vis_gx1 = self._visible_glass_bounds(progress)
        if show_glass:
            self._draw_sky_and_moon(canvas, t, gx0, gy0_py, vis_gx0, vis_gx1)
            self._draw_landscape_and_pines(canvas, gx0, gy0_py, vis_gx0, vis_gx1)
            self._draw_snowfall_and_glaze(
                canvas, t, gx0, gy0_py, vis_gx0, vis_gx1, lights_on=lights_on, reflect_p=reflect_p
            )
        self._draw_oak_frame(canvas, x0, y0, min_py=frame_min_py)

    def _visible_glass_bounds(self, progress: float) -> tuple[bool, int, int]:
        """Compute horizontally parted vista window bounds during intro reveal."""
        if progress >= 1.0:
            return True, 0, self.glass_w - 1
        open_t = max(0.0, min(1.0, (progress - 0.18) / 0.82))
        if open_t <= 0.0:
            return False, 0, -1
        open_e = 1.0 - (1.0 - open_t) ** 2
        mid_gx = self.glass_w // 2
        half_open = int(round((self.glass_w / 2.0 + 1.0) * open_e))
        return True, max(0, mid_gx - half_open), min(self.glass_w - 1, mid_gx + half_open)

    def _draw_sky_and_moon(
        self,
        canvas: Canvas,
        t: float,
        gx0: int,
        gy0_py: int,
        vis_gx0: int,
        vis_gx1: int,
    ) -> None:
        """Render twilight sky gradient, twinkling stars, drifting clouds, and 3D crescent moon."""
        moon_gx, moon_dy = 19, 4
        moon_cx, moon_cy = gx0 + moon_gx, gy0_py + moon_dy

        # 1. Atmospheric twilight sky gradient + soft radial moon halo
        horizon_col = (38, 56, 98)
        for dy in range(self.glass_px_h):
            py = gy0_py + dy
            sky_t = dy / max(1, self.glass_px_h - 5)
            sky_col = lerp_rgb(NIGHT_SKY_TOP, NIGHT_SKY_BOT, min(1.0, sky_t))
            if dy >= 11:
                sky_col = lerp_rgb(sky_col, horizon_col, min(1.0, (dy - 11) / 6.0) * 0.55)
            for dx in range(vis_gx0, vis_gx1 + 1):
                px = gx0 + dx
                dist_moon = math.hypot(px - moon_cx, py - moon_cy)
                col = sky_col
                if dist_moon < 8.0:
                    halo = max(0.0, 1.0 - dist_moon / 8.0)
                    col = lerp_rgb(col, (148, 166, 208), halo * 0.22)
                    col = lerp_rgb(col, MOON_YELLOW, (halo ** 2) * 0.24)
                canvas.set_px(px, py, col)

        # 2. Twinkling stars in upper sky
        for sx, sdy, phase, base_b in self.stars:
            if vis_gx0 <= sx <= vis_gx1 and 0 <= sdy < 10:
                twinkle = round((0.45 + 0.55 * math.sin(t * 2.4 + phase)) * 4.0) / 4.0
                canvas.blend_px(gx0 + sx, gy0_py + sdy, STAR_WHITE, base_b * twinkle)

        # 3. Wispy drifting night clouds catching silver-gold moonlight (stepped for atlas stability)
        cloud_shift = int(t * 1.2) * 0.5
        for dy in (2, 3, 6, 7):
            band_phase = 0.0 if dy <= 3 else 3.1
            for dx in range(vis_gx0, vis_gx1 + 1):
                wisp = math.sin((dx - cloud_shift * (1.0 if dy <= 3 else 0.7)) * 0.36 + band_phase)
                wisp2 = math.cos((dx + cloud_shift * 0.3) * 0.21 + dy)
                density = wisp * 0.55 + wisp2 * 0.45
                if density > 0.38:
                    alpha = 0.14 if density < 0.58 else (0.24 if density < 0.78 else 0.32)
                    dist_moon = math.hypot(dx - moon_gx, dy - moon_dy)
                    cloud_col = lerp_rgb((74, 96, 142), (218, 212, 184), max(0.0, 1.0 - dist_moon / 9.0))
                    canvas.blend_px(gx0 + dx, gy0_py + dy, cloud_col, alpha)

        # 4. Smooth 3D crescent moon with earthshine & lunar surface shading
        moon_ivory = (255, 248, 222)
        moon_earthshine = (46, 62, 102)
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                gx = moon_gx + dx
                mdy = moon_dy + dy
                if not (vis_gx0 <= gx <= vis_gx1 and 0 <= mdy < self.glass_px_h):
                    continue
                d_main = math.hypot(dx, dy)
                cov = max(0.0, min(1.0, (3.25 - d_main) / 0.85))
                if cov <= 0.0:
                    continue
                d_cut = math.hypot(dx - 1.55, dy + 0.55)
                lit = max(0.0, min(1.0, (d_cut - 2.05) / 1.15))
                mare = 0.94 + 0.06 * math.sin(dx * 1.9 + dy * 2.3)
                lit_col = scale_rgb(lerp_rgb(MOON_YELLOW, moon_ivory, lit * 0.7), mare)
                canvas.blend_px(gx0 + gx, gy0_py + mdy, lerp_rgb(moon_earthshine, lit_col, lit), cov)

    def _draw_landscape_and_pines(
        self,
        canvas: Canvas,
        gx0: int,
        gy0_py: int,
        vis_gx0: int,
        vis_gx1: int,
    ) -> None:
        """Render moonlit alpine mountain ridge, rolling snow hills, and pine forest."""
        ridge_heights = (
            13, 12, 11, 10, 11, 12, 13, 13, 12, 11, 12, 13, 14,
            13, 12, 11, 10, 10, 11, 12, 13, 12, 11, 12, 13,
        )
        for dx in range(vis_gx0, vis_gx1 + 1):
            crest_dy = ridge_heights[dx % len(ridge_heights)]
            prev_dy = ridge_heights[(dx - 1) % len(ridge_heights)]
            is_moonlit_slope = crest_dy <= prev_dy
            for dy in range(crest_dy, 17):
                if dy == crest_dy:
                    col = (108, 134, 178) if is_moonlit_slope else (52, 70, 110)
                else:
                    col = (64, 86, 130) if is_moonlit_slope else (30, 44, 78)
                if dy >= 14:
                    col = lerp_rgb(col, (56, 78, 118), (dy - 13) / 4.0)
                canvas.set_px(gx0 + dx, gy0_py + dy, col)

        for dx in range(vis_gx0, vis_gx1 + 1):
            px = gx0 + dx
            hill_top = 16 + int(round(math.sin(dx * 0.25 + 0.6) * 1.2))
            for dy in range(hill_top, self.glass_px_h):
                if dy == hill_top:
                    col = (204, 222, 248)
                else:
                    col = lerp_rgb(HILL_SNOW, HILL_DARK, min(1.0, (dy - hill_top) / 5.0))
                canvas.set_px(px, gy0_py + dy, col)

        pines = ((1, 17, 6), (5, 17, 7), (8, 16, 5), (15, 17, 7), (18, 16, 5), (22, 17, 8))
        for tree_gx, base_dy, tree_h in pines:
            for step in range(tree_h):
                half = 1 + step // 2
                dy = base_dy - (tree_h - 1 - step)
                if dy < 0 or dy >= self.glass_px_h:
                    continue
                for ox in range(-half + 1, half):
                    gx = tree_gx + ox
                    if vis_gx0 <= gx <= vis_gx1:
                        is_snow_cap = (step % 2 == 0 and ox >= 0) or step == 0
                        col = (164, 190, 224) if is_snow_cap else scale_rgb(PINE_DARK, 0.88)
                        canvas.set_px(gx0 + gx, gy0_py + dy, col)

    def _draw_snowfall_and_glaze(
        self,
        canvas: Canvas,
        t: float,
        gx0: int,
        gy0_py: int,
        vis_gx0: int,
        vis_gx1: int,
        lights_on: bool = True,
        reflect_p: float = 1.0,
    ) -> None:
        """Render FPS-independent 3-depth falling snow, frosted glass corners, and sill snow."""
        ticks = t * 20.0
        max_snow_dy = self.glass_px_h - 2
        for idx, flake in enumerate(self.flakes):
            init_x = float(flake[0])
            init_y = float(flake[1])
            speed_y = float(flake[2])
            wind_scale = float(flake[3])
            flutter_phase = float(flake[4])
            flutter_freq = float(flake[5])
            layer = int(flake[6])

            total_y = init_y + speed_y * ticks
            wrap_count = int(total_y // max_snow_dy)
            py_f = total_y % max_snow_dy
            start_x = init_x if wrap_count == 0 else hash01(idx, wrap_count) * self.glass_w
            drift_x = (-0.055 * ticks + 0.03 * math.sin(t * 0.45) * 4.0) * wind_scale
            flutter_x = math.sin(t * flutter_freq + flutter_phase) * 0.65
            fx = int((start_x + drift_x + flutter_x) % self.glass_w)
            if not (vis_gx0 <= fx <= vis_gx1):
                continue

            dy0 = int(py_f)
            frac = py_f - dy0
            frac_q = 0.0 if frac < 0.32 else (0.5 if frac < 0.68 else 1.0)
            if layer == 0:
                col, base_alpha = SNOW_SOFT, 0.45
            elif layer == 1:
                col, base_alpha = lerp_rgb(SNOW_SOFT, SNOW_WHITE, 0.55), 0.72
            else:
                col, base_alpha = SNOW_WHITE, 0.95

            if 0 <= dy0 < max_snow_dy and frac_q < 1.0:
                canvas.blend_px(gx0 + fx, gy0_py + dy0, col, base_alpha * (1.0 - frac_q))
            if 0 <= dy0 + 1 < max_snow_dy and frac_q > 0.0:
                canvas.blend_px(gx0 + fx, gy0_py + dy0 + 1, col, base_alpha * frac_q)

        for corner_gx in (0, self.glass_w - 1):
            if vis_gx0 <= corner_gx <= vis_gx1:
                canvas.blend_px(gx0 + corner_gx, gy0_py, SNOW_WHITE, 0.25)
                canvas.blend_px(gx0 + corner_gx, gy0_py + 1, SNOW_SOFT, 0.18)
        for dx in range(vis_gx0, vis_gx1 + 1):
            drift = 2 if math.sin(dx * 0.48) > 0.2 else 1
            for dh in range(drift):
                canvas.set_px(gx0 + dx, gy0_py + self.glass_px_h - 1 - dh, SNOW_WHITE)

        for step in range(4):
            if vis_gx0 <= 2 + step <= vis_gx1:
                canvas.blend_px(gx0 + 2 + step, gy0_py + 2 + step, (198, 220, 250), 0.16)
            if vis_gx0 <= 15 + step <= vis_gx1:
                canvas.blend_px(gx0 + 15 + step, gy0_py + 14 + step, (198, 220, 250), 0.14)

        if lights_on and reflect_p > 0.02:
            # Faint warm interior ghost-reflections of the tree/room warmth on cold dark glass panes
            warm_reflections = ((1, 11, 0.16), (2, 12, 0.22), (3, 14, 0.15), (14, 12, 0.12), (15, 13, 0.16))
            refl_scale = max(0.0, min(1.0, reflect_p))
            for rgx, rdy, ralpha in warm_reflections:
                if vis_gx0 <= rgx <= vis_gx1:
                    canvas.blend_px(gx0 + rgx, gy0_py + rdy, FLOOR_WARM_GLOW, ralpha * refl_scale)

    def _draw_oak_frame(self, canvas: Canvas, x0: int, y0: int, min_py: int = 0) -> None:
        """Draw 4-tone wood-grained oak window frame, inner reveal shadows, sash, and sill."""
        py_top = y0 * 2                 # py = 8
        py_bot = (y0 + self.h - 1) * 2  # py = 32
        mid_x = x0 + self.w // 2        # x = 98
        mid_py = py_top + 12            # py = 20

        oak_hi = lerp_rgb(WINDOW_FRAME, WALL_TREE_GLOW, 0.28)
        oak_mid = WINDOW_FRAME
        oak_grain = scale_rgb(WINDOW_FRAME, 0.86)
        oak_lo = scale_rgb(TABLE_WOOD, 0.68)

        # Cast subtle frame shadows onto the glass panes (depth reveal)
        for dx in range(1, self.w - 1):
            px = x0 + dx
            if py_top + 2 >= min_py:
                canvas.blend_px(px, py_top + 2, SHADOW_PLUM, 0.36)
            if px != mid_x and mid_py + 1 >= min_py:
                canvas.blend_px(px, mid_py + 1, SHADOW_PLUM, 0.30)
        for py in range(max(min_py, py_top + 2), py_bot):
            canvas.blend_px(x0 + 1, py, SHADOW_PLUM, 0.26)
            canvas.blend_px(mid_x + 1, py, SHADOW_PLUM, 0.22)

        # Top horizontal casing with subtle wood-grain streaks (py = 8..9)
        for dx in range(self.w):
            px = x0 + dx
            grain = oak_hi if (dx % 5 != 0) else oak_mid
            if py_top >= min_py:
                canvas.set_px(px, py_top, grain)
            if py_top + 1 >= min_py:
                canvas.set_px(px, py_top + 1, oak_lo if dx % 4 != 0 else oak_grain)

        # Left/right vertical jambs & center mullion with vertical wood grain
        for py in range(max(min_py, py_top + 2), py_bot):
            grain_l = oak_hi if (py % 4 != 0) else oak_mid
            grain_r = oak_lo if (py % 3 != 0) else oak_grain
            grain_m = oak_mid if (py % 4 != 0) else oak_grain
            canvas.set_px(x0, py, grain_l)
            canvas.set_px(x0 + self.w - 1, py, grain_r)
            canvas.set_px(mid_x, py, grain_m)

        # Thin horizontal sash bar with snow dust resting on top
        for dx in range(1, self.w - 1):
            px = x0 + dx
            if mid_py >= min_py:
                canvas.set_px(px, mid_py, oak_hi if dx % 6 == 0 else oak_mid)
            if dx % 3 != 0 and px != mid_x and mid_py - 1 >= min_py:
                canvas.blend_px(px, mid_py - 1, SNOW_WHITE, 0.36)

        # Molded oak sill (py = 32..33) + under-sill apron (py = 34) + wall AO shadow (py = 35)
        for dx in range(-1, self.w + 1):
            px = x0 + dx
            warm = 0.16 if dx < self.w // 2 else 0.0
            sill_top = lerp_rgb(oak_hi if dx % 5 != 0 else oak_mid, FLOOR_WARM_GLOW, warm)
            if py_bot >= min_py:
                canvas.set_px(px, py_bot, sill_top)
            if py_bot + 1 >= min_py:
                canvas.set_px(px, py_bot + 1, oak_lo)
            if 0 <= dx < self.w:
                if py_bot + 2 >= min_py:
                    canvas.set_px(px, py_bot + 2, scale_rgb(oak_lo, 0.85))
                if py_bot + 3 >= min_py:
                    canvas.blend_px(px, py_bot + 3, SHADOW_PLUM, 0.45)
            elif py_bot + 2 >= min_py:
                canvas.blend_px(px, py_bot + 2, SHADOW_PLUM, 0.45)
