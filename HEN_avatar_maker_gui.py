"""Safe desktop entry point for HEN Avatar Maker."""

from __future__ import annotations

import sys
import traceback


def main() -> int:
    try:
        from hen_avatar_maker.app import run

        return run()
    except Exception as exc:  # Last-resort startup guard for double-click launches.
        message = (
            "HEN Avatar Maker could not start.\n\n"
            f"Error: {exc}\n\n"
            "Run the application from a terminal to see the full traceback."
        )
        print(traceback.format_exc(), file=sys.stderr)

        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(0, message, "HEN Avatar Maker", 0x10)
            except Exception:
                pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
