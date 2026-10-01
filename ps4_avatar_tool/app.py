from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from .config import APP_TITLE
from .ui.main_window import MainWindow


LOG_DIR = Path.home() / "PS4 Avatar Tool" / "logs"
LOG_FILE = LOG_DIR / "application.log"

LOGGER = logging.getLogger(__name__)


class SafeApplication(QApplication):
    """
    QApplication with a deferred fatal-error dialog.

    Never create a modal QMessageBox directly from an event handler. In
    particular, doing so during painting can interfere with Qt's backing-store
    paint transaction.
    """

    _fatal_pending = False

    def notify(self, receiver, event):  # type: ignore[override]
        try:
            return super().notify(receiver, event)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()

            details = "".join(
                traceback.format_exception(
                    exc_type,
                    exc_value,
                    exc_traceback,
                )
            )

            LOGGER.critical(
                "Unhandled Qt event exception:\n%s",
                details,
            )

            self._schedule_fatal_dialog(exc_value)
            return False

    def _schedule_fatal_dialog(
        self,
        exc_value: BaseException | None,
    ) -> None:
        if self._fatal_pending:
            return

        self._fatal_pending = True

        error_type = (
            type(exc_value).__name__
            if exc_value is not None
            else "UnknownError"
        )

        error_message = (
            str(exc_value)
            if exc_value is not None
            else "No additional error information was available."
        )

        message = (
            f"{APP_TITLE} encountered an unexpected error.\n\n"
            f"{error_type}: {error_message}\n\n"
            "A diagnostic log was written to:\n"
            f"{LOG_FILE}"
        )

        def show_dialog() -> None:
            try:
                QMessageBox.critical(
                    None,
                    APP_TITLE,
                    message,
                )
            except Exception:
                LOGGER.exception("Failed to display fatal-error dialog.")
            finally:
                self._fatal_pending = False

        QTimer.singleShot(0, show_dialog)


def _configure_logging() -> None:
    """
    Configure persistent application logging.

    Logging failures must never prevent the GUI from starting.
    """
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format=(
                "%(asctime)s | "
                "%(levelname)s | "
                "%(name)s | "
                "%(message)s"
            ),
            encoding="utf-8",
        )
    except Exception:
        # A logging failure should never become an application startup failure.
        pass


def _install_python_exception_hook(
    app: SafeApplication,
) -> None:
    """
    Handle uncaught Python exceptions outside Qt event dispatch.
    """

    def excepthook(
        exc_type,
        exc_value,
        exc_traceback,
    ) -> None:
        details = "".join(
            traceback.format_exception(
                exc_type,
                exc_value,
                exc_traceback,
            )
        )

        LOGGER.critical(
            "Unhandled Python exception:\n%s",
            details,
        )

        app._schedule_fatal_dialog(exc_value)

    sys.excepthook = excepthook


def create_application(
    icon_path: Path | None = None,
) -> SafeApplication:
    """
    Create and configure the Qt application instance.
    """
    existing = QApplication.instance()

    if isinstance(existing, SafeApplication):
        app = existing
    elif existing is not None:
        raise RuntimeError(
            "A QApplication already exists with an incompatible type."
        )
    else:
        SafeApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = SafeApplication(sys.argv)

    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("DJO'S")
    app.setApplicationVersion("1.0.0")

    if icon_path is not None and icon_path.is_file():
        icon = QIcon(str(icon_path))

        if not icon.isNull():
            app.setWindowIcon(icon)
            LOGGER.info("Application icon loaded from %s", icon_path)
        else:
            LOGGER.warning(
                "Qt could not load application icon: %s",
                icon_path,
            )
    else:
        LOGGER.warning(
            "Application icon not found: %s",
            icon_path,
        )

    return app


def run(
    *,
    icon_path: Path | None = None,
) -> int:
    """
    Start the application.

    Parameters
    ----------
    icon_path:
        Optional path to the application's .ico file.
    """
    _configure_logging()

    app = create_application(icon_path)
    _install_python_exception_hook(app)

    LOGGER.info("Starting %s", APP_TITLE)

    window = MainWindow()

    if icon_path is not None and icon_path.is_file():
        icon = QIcon(str(icon_path))

        if not icon.isNull():
            window.setWindowIcon(icon)

    window.show()

    return app.exec()