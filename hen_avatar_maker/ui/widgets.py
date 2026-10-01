from __future__ import annotations

from PIL import Image
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QFrame, QPushButton, QSizePolicy, QWidget

from ..config import THEME
from ..qt_image import pil_to_qpixmap


def qcolor(value: str) -> QColor:
    """Convert a theme hex value explicitly for Qt painting APIs."""
    return QColor(value)


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            f"QFrame#Card {{ background: {THEME.panel}; border: 1px solid {THEME.border}; border-radius: 6px; }}"
        )


class IconButton(QPushButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(42, 42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Choose a folder")
        self.setAccessibleName("Choose export folder")

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(qcolor(THEME.text))
        pen.setWidthF(1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        x, y, w, h = 12.0, 13.0, 18.0, 14.0
        painter.drawRoundedRect(QRectF(x, y + 4.0, w, h - 4.0), 2.0, 2.0)
        painter.drawLine(QPointF(x + 2, y + 4), QPointF(x + 7, y + 4))
        painter.drawLine(QPointF(x + 7, y + 4), QPointF(x + 9, y + 7))
        painter.end()


class ToggleSwitch(QWidget):
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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        radius = self.height() / 2.0
        track = qcolor(THEME.blue if self._checked else THEME.border_light)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track))
        painter.drawRoundedRect(self.rect(), radius, radius)

        knob_margin = 4.0
        knob_size = self.height() - 2.0 * knob_margin
        knob_x = self.width() - knob_size - knob_margin if self._checked else knob_margin
        painter.setBrush(QBrush(qcolor(THEME.white)))
        painter.drawEllipse(int(knob_x), int(knob_margin), int(knob_size), int(knob_size))
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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pen = QPen(qcolor(THEME.border_light))
        pen.setWidthF(1.5)
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
        painter.drawLine(QPointF(cx, 34), QPointF(cx, 64))
        painter.drawLine(QPointF(cx, 34), QPointF(cx - 10, 44))
        painter.drawLine(QPointF(cx, 34), QPointF(cx + 10, 44))
        painter.drawArc(int(cx - 28), 49, 56, 35, 205 * 16, 130 * 16)

        title = painter.font()
        title.setPointSize(11)
        title.setBold(True)
        painter.setFont(title)
        painter.setPen(qcolor(THEME.text))
        painter.drawText(0, 80, self.width(), 28, Qt.AlignmentFlag.AlignCenter, "Drop Image Here")

        body = painter.font()
        body.setPointSize(9)
        body.setBold(False)
        painter.setFont(body)
        painter.setPen(qcolor(THEME.muted))
        painter.drawText(0, 108, self.width(), 20, Qt.AlignmentFlag.AlignCenter, "or")

        body.setBold(True)
        painter.setFont(body)
        painter.setPen(qcolor(THEME.text))
        painter.drawText(0, 130, self.width(), 24, Qt.AlignmentFlag.AlignCenter, "Click to Import")
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


class ProfilePreview(QWidget):
    clicked = pyqtSignal(bool)

    def __init__(self, round_mode: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.round_mode = round_mode
        self._selected = False
        self._hovered = False
        self._pixmap: QPixmap | None = None
        self.setFixedSize(86, 86)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Round profile preview" if round_mode else "Square profile preview")

    def setImage(self, image: Image.Image | None) -> None:
        self._pixmap = pil_to_qpixmap(image) if image is not None else None
        self.update()

    def setSelected(self, selected: bool) -> None:
        self._selected = bool(selected)
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
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clicked.emit(self.round_mode)
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if self._selected:
            border = qcolor(THEME.white)
        elif self._hovered or self.hasFocus():
            border = qcolor(THEME.blue)
        else:
            border = qcolor(THEME.border_light)

        pen = QPen(border)
        pen.setWidthF(1.5)
        painter.setPen(pen)
        painter.setBrush(QBrush(qcolor("#303239")))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        content = self.rect().adjusted(9, 9, -9, -9)
        if self._pixmap is None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(qcolor(THEME.placeholder)))
            painter.drawRect(content)
            painter.setBrush(QBrush(qcolor(THEME.placeholder_light)))
            center = content.center()
            painter.drawEllipse(center.x() - 12, content.top() + 11, 24, 24)
            painter.drawPie(center.x() - 25, content.top() + 34, 50, 30, 0, 180 * 16)
        else:
            source = self._pixmap
            target_width = max(1, content.width())
            target_height = max(1, content.height())
            fitted = source.scaled(
                target_width,
                target_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            top_left = content.center() - fitted.rect().center()
            if self.round_mode:
                painter.save()
                painter.setClipPath(self._circle_path(content))
                painter.drawPixmap(top_left, fitted)
                painter.restore()
            else:
                painter.drawPixmap(top_left, fitted)

        if self.round_mode:
            ring_pen = QPen(qcolor(THEME.blue if self._selected else border))
            ring_pen.setWidthF(1.8)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(content)

        painter.end()

    @staticmethod
    def _circle_path(rect) -> QPainterPath:
        path = QPainterPath()
        path.addEllipse(rect)
        return path
