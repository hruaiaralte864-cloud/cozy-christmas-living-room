"""CLI entrypoint for the ASCII Christmas Living Room terminal animation."""

from __future__ import annotations

import argparse
import sys

from scene import LivingRoomRenderer, enable_windows_ansi


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line options for running or previewing the scene."""
    parser = argparse.ArgumentParser(
        prog="ascii-christmas-living-room",
        description="Animated 24-bit TrueColor ASCII Christmas living room for your terminal.",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help="Target animation frames per second (default: 30).",
    )
    parser.add_argument(
        "--no-intro",
        action="store_true",
        help="Skip the step-by-step build-up animation and jump straight to the cozy loop.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Intro build-up speed multiplier, e.g. 2.0 for 2x faster (default: 1.0).",
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="Print a single full TrueColor frame and exit (useful for snapshots).",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="With --static, print plain ASCII characters without ANSI color codes.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the terminal animation or print a static snapshot."""
    args = parse_args(argv)
    renderer = LivingRoomRenderer(
        fps=args.fps,
        skip_intro=args.no_intro,
        intro_speed=args.speed,
    )

    if args.static:
        enable_windows_ansi()
        canvas = renderer.render_frame(t=1.25, intro_elapsed=None)
        if args.plain:
            print(canvas.to_ansi(plain=True))
        else:
            sys.stdout.write(canvas.to_ansi().replace("\x1b[H", "") + "\n")
            sys.stdout.flush()
        return 0

    renderer.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
