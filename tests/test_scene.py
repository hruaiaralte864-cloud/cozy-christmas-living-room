"""Unit tests for the Sub-Pixel + Glyph Hybrid Christmas Living Room scene."""

from __future__ import annotations

import unittest
import unicodedata

from christmas import parse_args
from scene.canvas import Canvas
from scene.presents import DEFAULT_PRESENTS
from scene.renderer import LivingRoomRenderer


class TestLivingRoomScene(unittest.TestCase):
    """Verify canvas boundaries, diff rendering, build stages, and frame serialization."""

    def test_canvas_clipping_and_plain_output(self) -> None:
        canvas = Canvas(width=10, height=5)
        canvas.put(-1, 0, "X", (255, 0, 0))
        canvas.put(10, 0, "X", (255, 0, 0))
        canvas.set_px(1, 0, (255, 220, 120))
        canvas.set_px(1, 1, (20, 40, 80))
        canvas.put(2, 2, "*", (255, 255, 0))
        cell = canvas.get(1, 0)
        self.assertIsNotNone(cell)
        self.assertEqual(cell.char, "▀")
        plain = canvas.to_ansi(plain=True).splitlines()
        self.assertEqual(len(plain), 5)
        self.assertEqual(len(plain[2]), 10)
        self.assertEqual(plain[2][2], "*")

    def test_diff_ansi_emits_only_changed_cells(self) -> None:
        canvas = Canvas(width=12, height=4)
        canvas.put(3, 1, "*", (255, 220, 90))
        full_payload, snap = canvas.to_ansi_diff(None)
        self.assertIn("\x1b[?2026h", full_payload)
        self.assertIn("\x1b[2J", full_payload)
        self.assertIn("\x1b[?2026l", full_payload)

        # Unchanged frame should emit zero cell draws
        noop_payload, snap2 = canvas.to_ansi_diff(snap)
        self.assertNotIn("*", noop_payload)
        self.assertNotIn("\x1b[2J", noop_payload)
        self.assertLess(len(noop_payload), 30)

        # Single changed cell should emit exact 1-based cursor coordinates (row 2, col 4)
        canvas.put(3, 1, "●", (255, 80, 80))
        delta_payload, _ = canvas.to_ansi_diff(snap2)
        self.assertIn("\x1b[2;4H", delta_payload)
        self.assertIn("●", delta_payload)

    def test_intro_stages_and_full_frame(self) -> None:
        renderer = LivingRoomRenderer()
        for elapsed in (0.3, 1.5, 2.3, 3.3, 4.5, 5.8, None):
            canvas = renderer.render_frame(t=2.5, intro_elapsed=elapsed)
            plain = canvas.to_ansi(plain=True)
            lines = plain.splitlines()
            self.assertEqual(len(lines), LivingRoomRenderer.HEIGHT)
            self.assertTrue(all(len(line) == LivingRoomRenderer.WIDTH for line in lines))
            # Ensure no wide/fullwidth or fallback Dingbat star glyphs that clip in monospace cells
            self.assertTrue(
                all(
                    unicodedata.east_asian_width(ch) not in ("W", "F") and ch not in ("✦", "✧")
                    for line in lines
                    for ch in line
                )
            )

        # Act 2 (s=2.8): hearth fire is burning while electric lights haven't awakened yet
        act2_canvas = renderer.render_frame(t=2.8, intro_elapsed=2.8)
        self.assertGreater(act2_canvas.get_px(15, 43)[0], 200)
        self.assertLess(act2_canvas.get_px(76, 20)[0], 60)

        # Act 3 (s=5.05): star unfolds cleanly at spire without overflowing onto ceiling beam (py=1)
        act3_canvas = renderer.render_frame(t=5.05, intro_elapsed=5.05)
        self.assertLess(max(act3_canvas.get_px(58, 1)), 120)

        # Negative elapsed clamps safely & small terminal dimensions trigger size warning cleanly
        neg_canvas = renderer.render_frame(t=0.0, intro_elapsed=-0.2, terminal_size=(60, 20))
        self.assertIn("60x20", neg_canvas.to_ansi(plain=True))

    def test_full_frame_contains_key_room_elements(self) -> None:
        renderer = LivingRoomRenderer()
        canvas = renderer.render_frame(t=1.0, intro_elapsed=None)
        plain = canvas.to_ansi(plain=True)
        ansi = canvas.to_ansi()
        self.assertIn("Cozy Christmas Living Room", plain)
        self.assertIn("▀", ansi)
        # Starburst topper core at (58, 6) and crescent moon limb at (103, 14) should be bright
        star_px = canvas.get_px(58, 6)
        self.assertGreater(star_px[0], 220)
        self.assertGreater(star_px[1], 200)
        moon_px = canvas.get_px(103, 14)
        self.assertGreater(moon_px[0], 200)
        self.assertGreater(moon_px[1], 190)
        # Mantel Little Drummer Boy brass shako emblem (7, 12) and scarlet tunic (6, 17)
        shako_brass = canvas.get_px(7, 12)
        self.assertGreater(shako_brass[0], 200)
        self.assertGreater(shako_brass[1], 150)
        tunic_px = canvas.get_px(6, 17)
        self.assertGreater(tunic_px[0], 150)
        # Lower shelf vintage tabletop radio: chrome antenna (39, 18), glowing dial (37, 22), playing note
        antenna_px = canvas.get_px(39, 18)
        self.assertGreater(min(antenna_px), 190)
        radio_dial_px = canvas.get_px(37, 22)
        self.assertGreater(radio_dial_px[0], 210)
        self.assertGreater(radio_dial_px[1], 160)
        # At t=0.72 (Phrase 1 droop-flag eighth note @ 34,17): head/stem bright while py=16 stays clear
        canvas_note1 = renderer.render_frame(t=0.72, intro_elapsed=None)
        self.assertGreater(canvas_note1.get_px(34, 19)[0], 200)
        self.assertLess(canvas_note1.get_px(34, 16)[0], 80)
        # At t=2.10 (Phrase 2 slender quarter note @ 35,17): companion note visible while Phrase 1 clears
        canvas_note2 = renderer.render_frame(t=2.10, intro_elapsed=None)
        self.assertGreater(canvas_note2.get_px(35, 19)[0], 190)
        self.assertLess(canvas_note2.get_px(34, 19)[0], 140)
        # Old trailing ivy below shelf ledge (29, 28) is removed cleanly
        below_shelf_px = canvas.get_px(29, 28)
        self.assertGreater(below_shelf_px[0], below_shelf_px[1])
        self.assertGreaterEqual(len(DEFAULT_PRESENTS), 8)

    def test_lights_toggle_and_cli_args(self) -> None:
        defaults = parse_args([])
        self.assertEqual(defaults.fps, 30.0)

        args = parse_args(["--static", "--plain", "--no-intro", "--fps", "24", "--speed", "2.0"])
        self.assertTrue(args.static)
        self.assertTrue(args.plain)
        self.assertTrue(args.no_intro)
        self.assertEqual(args.fps, 24.0)
        self.assertEqual(args.speed, 2.0)

        renderer = LivingRoomRenderer()
        renderer.lights_on = False
        canvas_off = renderer.render_frame(t=0.5)
        ansi = canvas_off.to_ansi()
        self.assertIn("\x1b[38;2;", ansi)

        star_rgb = canvas_off.get_px(58, 6)
        self.assertLess(max(star_rgb), 160)

        hearth_rgb = canvas_off.get_px(15, 43)
        self.assertGreater(hearth_rgb[0], 200)

        right_wall_rgb = canvas_off.get_px(76, 20)
        self.assertLess(right_wall_rgb[0], 60)

        # Powered backlit radio dial (37, 22) dims off cleanly in Midnight Hearth mode
        radio_dial_off = canvas_off.get_px(37, 22)
        self.assertLess(max(radio_dial_off), 80)

    def test_render_frame_is_idempotent_at_fixed_time(self) -> None:
        renderer = LivingRoomRenderer()
        first = renderer.render_frame(t=1.25, intro_elapsed=None).to_ansi(plain=True)
        second = renderer.render_frame(t=1.25, intro_elapsed=None).to_ansi(plain=True)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
