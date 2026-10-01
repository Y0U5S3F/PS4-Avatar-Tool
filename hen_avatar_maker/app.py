from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from .config import APP_TITLE
from .ui.main_window import MainWindow


LOG_DIR = Path.home() / "PS4 Avatar Tool" / "logs"
LOG_FILE = LOG_DIR / "application.log"


class SafeApplication(QApplication):
    """QApplication that never opens a modal dialog from inside an event handler.

    Qt paints widgets inside a platform-managed paint cycle. Showing a modal dialog
    from an exception handler while that cycle is still active can produce errors
    such as ``QBackingStore::endPaint() called with active painter``.  We log the
    exception immediately and defer the diagnostic dialog until the event loop is
    idle.
    """

    _fatal_pending = False

    def notify(self, receiver, event):  # type: ignore[override]
        try:
            return super().notify(receiver, event)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logging.critical("Unhandled Qt event exception:\n%s", details)
            self._schedule_fatal_dialog(exc_value)
            return False

    def _schedule_fatal_dialog(self, exc_value: BaseException | None) -> None:
        if self._fatal_pending:
            return
        self._fatal_pending = True
        message = (
            f"{APP_TITLE} encountered an unexpected error.\n\n"
            f"{type(exc_value).__name__}: {exc_value}\n\n"
            f"A diagnostic log was written to:\n{LOG_FILE}"
        )

        def show() -> None:
            try:
                QMessageBox.critical(None, APP_TITLE, message)
            finally:
                self._fatal_pending = False

        QTimer.singleShot(0, show)


def _configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        encoding="utf-8",
    )


def _install_python_exception_hook(app: SafeApplication) -> None:
    """Handle exceptions outside Qt event dispatch without interrupting painting."""

    def excepthook(exc_type, exc_value, exc_traceback) -> None:
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.critical("Unhandled Python exception:\n%s", details)
        app._schedule_fatal_dialog(exc_value)

    sys.excepthook = excepthook


def create_application() -> SafeApplication:
    existing = QApplication.instance()
    if isinstance(existing, SafeApplication):
        return existing
    if existing is not None:
        raise RuntimeError("A QApplication already exists with an incompatible type.")

    SafeApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = SafeApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("HEN Tools")
    app.setApplicationVersion("2.2.0")
    return app


def run() -> int:
    _configure_logging()
    app = create_application()
    _install_python_exception_hook(app)
    logging.info("Starting %s", APP_TITLE)

    window = MainWindow()
    window.show()
    return app.exec()
