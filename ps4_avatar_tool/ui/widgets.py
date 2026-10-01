from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QPushButton, QSizePolicy, QWidget

from ..config import THEME


def qcolor(value: str) -> QColor:
    return QColor(value)


def begin_paint(widget: QWidget) -> QPainter | None:
    """Begin a widget paint safely; callers must always end the returned painter."""
    painter = QPainter()
    if not painter.begin(widget):
        painter.dispose()
        return None
    return painter


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            f"QFrame#Card {{ background: {THEME.panel}; border: 1px solid {THEME.border}; border-radius: 6px; }}"
        )


class IconButton(QPushButton):
    """Folder button using Qt's native icon instead of a custom paint event."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(42, 42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Choose a folder")
        self.setAccessibleName("Choose export folder")
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_DirOpenIcon)
        self.setIcon(icon)
        self.setIconSize(self.iconSize() * 0.72)


class ToggleSwitch(QWidget):
    """Small custom switch. Painting is exception-safe and never leaks an active painter."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = bool(checked)
        self.setFixedSize(44, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Apply round profile crop")

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        checked = bool(checked)
        if checked == self._checked:
            return
        self._checked = checked
        self.update()
        self.toggled.emit(checked)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.setChecked(not self._checked)
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = begin_paint(self)
        if painter is None:
            return
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            radius = self.height() / 2.0
            track = qcolor(THEME.blue if self._checked else THEME.border_light)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(track))
            painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), radius, radius)

            margin = 4.0
            knob_size = self.height() - 2.0 * margin
            knob_x = self.width() - knob_size - margin if self._checked else margin
            painter.setBrush(QBrush(qcolor(THEME.white)))
            painter.drawEllipse(int(knob_x), int(margin), int(knob_size), int(knob_size))
        finally:
            if painter.isActive():
                painter.end()


class ImportDropZone(QFrame):
    clicked = pyqtSignal()
    fileDropped = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(320, 180)
        self.setMaximumSize(400, 190)
        self.setObjectName("ImportDropZone")
        self.setAccessibleName("Import image drop zone")
        self.setAccessibleDescription("Click to select an image or drag an image here")

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = begin_paint(self)
        if painter is None:
            return
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            pen = QPen(qcolor(THEME.border_light))
            pen.setWidthF(1.25)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(qcolor("#23252b")))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

            cx = self.width() / 2.0
            icon_pen = QPen(qcolor(THEME.icon))
            icon_pen.setWidthF(3.0)
            icon_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            icon_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(icon_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(cx, 34), QPointF(cx, 64))
            painter.drawLine(QPointF(cx, 34), QPointF(cx - 10, 44))
            painter.drawLine(QPointF(cx, 34), QPointF(cx + 10, 44))
            painter.drawArc(int(cx - 28), 49, 56, 35, 205 * 16, 130 * 16)

            font = painter.font()
            font.setPointSize(11)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(qcolor(THEME.text))
            painter.drawText(0, 80, self.width(), 28, Qt.AlignmentFlag.AlignCenter, "Drop Image Here")

            font.setPointSize(9)
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(qcolor(THEME.muted))
            painter.drawText(0, 108, self.width(), 20, Qt.AlignmentFlag.AlignCenter, "or")

            font.setBold(True)
            painter.setFont(font)
            painter.setPen(qcolor(THEME.text))
            painter.drawText(0, 130, self.width(), 24, Qt.AlignmentFlag.AlignCenter, "Click to Import")
        finally:
            if painter.isActive():
                painter.end()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.fileDropped.emit(url.toLocalFile())
                event.acceptProposedAction()
                return
        event.ignore()
