from __future__ import annotations

from collections.abc import Callable

from PIL import Image
from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QFrame, QPushButton, QWidget

from ..config import THEME
from ..qt_image import pil_to_qimage


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setStyleSheet(
            f"QFrame#Card {{ background: {THEME.panel}; border: 1px solid {THEME.border}; border-radius: 6px; }}"
        )


class IconButton(QPushButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(42, 42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Choose a folder")
        self.setStyleSheet(
            f"""
            QPushButton {{ background: {THEME.panel_alt}; border: 0; border-radius: 5px; }}
            QPushButton:hover {{ background: {THEME.border_light}; }}
            QPushButton:pressed {{ background: {THEME.border}; }}
            """
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(THEME.text)
        pen.setWidth(1.8)
        painter.setPen(pen)
        x, y, w, h = 12, 14, 18, 14
        painter.drawRoundedRect(x, y + 3, w, h - 3, 2, 2)
        painter.drawLine(x + 2, y + 3, x + 7, y + 3)
        painter.drawLine(x + 7, y + 3, x + 9, y + 6)
        painter.end()


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(44, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        checked = bool(checked)
        if checked == self._checked:
            return
        self._checked = checked
        self.update()
        self.toggled.emit(checked)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        radius = self.height() / 2
        track = THEME.blue if self._checked else THEME.border_light
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track))
        painter.drawRoundedRect(self.rect(), radius, radius)

        knob_margin = 4
        knob_size = self.height() - 2 * knob_margin
        knob_x = self.width() - knob_size - knob_margin if self._checked else knob_margin
        painter.setBrush(QBrush(THEME.white))
        painter.drawEllipse(knob_x, knob_margin, knob_size, knob_size)
        painter.end()


class ImportDropZone(QFrame):
    clicked = pyqtSignal()
    fileDropped = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(300, 170)
        self.setMaximumSize(400, 190)
        self.setObjectName("ImportDropZone")

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(THEME.border_light)
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(THEME.panel_alt))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

        cx = self.width() / 2
        icon_pen = QPen("#9ea4b0")
        icon_pen.setWidth(3)
        icon_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        icon_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(icon_pen)
        painter.drawLine(QPointF(cx, 40), QPointF(cx, 72))
        painter.drawLine(QPointF(cx, 40), QPointF(cx - 11, 51))
        painter.drawLine(QPointF(cx, 40), QPointF(cx + 11, 51))
        painter.drawArc(int(cx - 28), 54, 56, 35, 205 * 16, 130 * 16)

        painter.setPen(QPen(THEME.text))
        title = painter.font()
        title.setPointSize(11)
        title.setBold(True)
        painter.setFont(title)
        painter.drawText(0, 103, self.width(), 24, Qt.AlignmentFlag.AlignCenter, "Drop Image Here")

        body = painter.font()
        body.setPointSize(9)
        body.setBold(False)
        painter.setFont(body)
        painter.setPen(QPen(THEME.muted))
        painter.drawText(0, 128, self.width(), 22, Qt.AlignmentFlag.AlignCenter, "or")
        title.setBold(True)
        title.setPointSize(9)
        painter.setFont(title)
        painter.setPen(QPen(THEME.text))
        painter.drawText(0, 149, self.width(), 24, Qt.AlignmentFlag.AlignCenter, "Click to Import")
        painter.end()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if any(url.isLocalFile() for url in urls):
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


class ProfilePreview(QWidget):
    clicked = pyqtSignal(bool)

    def __init__(self, round_mode: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.round_mode = round_mode
        self._selected = False
        self._hovered = False
        self._image: QImage | None = None
        self.setFixedSize(86, 86)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Round profile crop" if round_mode else "Square profile crop")

    def setImage(self, image: Image.Image | None) -> None:
        self._image = pil_to_qimage(image) if image is not None else None
        self.update()

    def setSelected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.round_mode)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        border = THEME.white if self._selected else THEME.border_light
        if self._hovered and not self._selected:
            border = THEME.blue

        painter.setPen(QPen(border, 1.5))
        painter.setBrush(QBrush(THEME.panel_alt))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        content = self.rect().adjusted(9, 9, -9, -9)
        if self._image is None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush("#5d626c"))
            painter.drawRect(content if not self.round_mode else content)
            painter.setBrush(QBrush("#9298a4"))
            painter.drawEllipse(content.center().x() - 12, content.top() + 11, 24, 24)
            painter.drawPie(content.center().x() - 25, content.top() + 34, 50, 30, 0, 180 * 16)
        else:
            source = QPixmap.fromImage(self._image)
            target = content
            scale = min(target.width() / source.width(), target.height() / source.height())
            fitted = source.scaled(
                int(source.width() * scale),
                int(source.height() * scale),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            top_left = target.center() - fitted.rect().center()
            if self.round_mode:
                painter.save()
                painter.setClipPath(self._circle_path(content))
                painter.drawPixmap(top_left, fitted)
                painter.restore()
            else:
                painter.drawPixmap(top_left, fitted)

        if self.round_mode:
            painter.setPen(QPen(THEME.blue if self._selected else border, 1.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(content)

        painter.end()

    @staticmethod
    def _circle_path(rect) :
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.addEllipse(rect)
        return path
