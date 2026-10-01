from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from .config import APP_TITLE
from .ui.main_window import MainWindow


_LOG_DIR = Path.home() / "HEN Avatar Maker" / "logs"
_LOG_FILE = _LOG_DIR / "application.log"


def _configure_logging() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=_LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _show_fatal_error(message: str) -> None:
    app = QApplication.instance()
    if app is not None:
        QMessageBox.critical(None, APP_TITLE, message)
        return

    print(message, file=sys.stderr)

    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message, APP_TITLE, 0x10)
        except Exception:
            pass


def _install_exception_hook() -> None:
    def excepthook(exc_type, exc_value, exc_traceback) -> None:
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.critical("Unhandled exception:\n%s", details)
        _show_fatal_error(
            "HEN Avatar Maker encountered an unexpected error.\n\n"
            f"A diagnostic log was written to:\n{_LOG_FILE}\n\n"
            f"Error: {exc_value}"
        )

    sys.excepthook = excepthook


def create_application() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("HEN Tools")
    app.setApplicationVersion("2.1.0")
    return app


def run() -> int:
    _configure_logging()
    _install_exception_hook()
    logging.info("Starting %s", APP_TITLE)

    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()
