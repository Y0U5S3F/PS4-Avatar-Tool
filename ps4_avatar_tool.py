"""Application entry point for PS4 Avatar Tool."""

from __future__ import annotations

import ctypes
import logging
import sys
import traceback
from pathlib import Path


APP_NAME = "PS4 Avatar Tool"


def resource_path(relative_path: str) -> Path:
    """
    Resolve a bundled resource in development and PyInstaller builds.
    """
    return Path(__file__).resolve().parent / relative_path


def show_fatal_error(message: str) -> None:
    """Show a Windows error dialog without risking another exception."""
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.user32.MessageBoxW(
            0,
            message,
            APP_NAME,
            0x10,
        )
    except Exception:
        pass


def main() -> int:
    try:
        from ps4_avatar_tool.app import run

        icon_path = resource_path("resources/tool.ico")

        return run(icon_path=icon_path)

    except Exception:
        details = traceback.format_exc()

        try:
            logging.critical(
                "Fatal startup exception:\n%s",
                details,
            )
        except Exception:
            pass

        show_fatal_error(
            f"{APP_NAME} could not start.\n\n"
            "A fatal startup error occurred.\n"
            "Check the application log for details."
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())