"""Desktop Tkinter window launcher for the Cozy Christmas Living Room animation."""

from __future__ import annotations

import sys

from christmas import main as cli_main


def main(argv: list[str] | None = None) -> int:
    """Launch the scene in a standalone Tkinter window, forwarding any CLI flags."""
    extra_args = sys.argv[1:] if argv is None else argv
    return cli_main(["--gui", *extra_args])


if __name__ == "__main__":
    raise SystemExit(main())
