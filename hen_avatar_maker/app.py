from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from .ui.main_window import MainWindow


def create_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QApplication(sys.argv)
    app.setApplicationName("HEN Avatar Maker")
    app.setOrganizationName("HEN Tools")
    return app


def main() -> int:
    app = create_app()
    window = MainWindow()
    window.show()
    return app.exec()
