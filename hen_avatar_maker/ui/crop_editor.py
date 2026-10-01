from __future__ import annotations

from collections.abc import Callable

from PIL import Image
from PyQt6.QtCore import QPointF, Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ..config import CROP_MAX_SIZE, CROP_MIN_SIZE, THEME, ZOOM_FACTOR, ZOOM_MAX, ZOOM_MIN
from ..qt_image import pil_to_qimage


class CropEditor(QWidget):
    """Painted crop editor: one source image, stable pan/zoom transforms, one overlay."""

    changed = pyqtSignal()
    resized = pyqtSignal()
    fileDropped = pyqtSignal(str)
    zoomChanged = pyqtSignal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._source: QImage | None = None
        self._source_size = (0, 0)
        self._scale = 1.0
        self._offset = QPointF(0.0, 0.0)
        self._crop_size = 420.0
        self._dragging = False
        self._last_mouse = QPointF()
        self._round = False

        self._pillow_image: Image.Image | None = None
        self._resized_cache: tuple[tuple[int, int], QImage] | None = None
        self._notify_change: Callable[[], None] | None = None

    @property
    def has_image(self) -> bool:
        return self._source is not None

    def set_change_callback(self, callback: Callable[[], None]) -> None:
        self._notify_change = callback

    def set_image(self, image: Image.Image) -> None:
        self._pillow_image = image.copy().convert("RGBA")
        self._source = pil_to_qimage(self._pillow_image)
        self._source_size = (self._source.width(), self._source.height())
        self._fit_image()
        self.update()
        self.changed.emit()
        if self._notify_change:
            self._notify_change()

    def set_round(self, enabled: bool) -> None:
        if self._round == enabled:
            return
        self._round = enabled
        self.update()
        self.changed.emit()
        if self._notify_change:
            self._notify_change()

    def resizeEvent(self, event) -> None:  # noqa: N802
        old_crop = self._crop_size
        self._update_crop_size()
        if self.has_image and self._crop_size > old_crop:
            self._ensure_crop_covered()
            self._clamp_offset()
        self.update()
        self.resized.emit()
        super().resizeEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.has_image:
            self._dragging = True
            self._last_mouse = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._dragging or not self.has_image:
            super().mouseMoveEvent(event)
            return
        delta = event.position() - self._last_mouse
        self._offset += delta
        self._last_mouse = event.position()
        self._clamp_offset()
        self.update()
        self.changed.emit()
        if self._notify_change:
            self._notify_change()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setCursor(Qt.CursorShape.CrossCursor)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802
        if not self.has_image:
            return
        angle = event.angleDelta().y()
        if angle == 0:
            return
        direction = 1 if angle > 0 else -1
        self._zoom(direction, event.position())
        event.accept()

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

    def _update_crop_size(self) -> None:
        width = max(self.width(), 1)
        height = max(self.height(), 1)
        self._crop_size = max(CROP_MIN_SIZE, min(CROP_MAX_SIZE, min(width - 60, height - 60)))

    def _fit_image(self) -> None:
        if not self.has_image:
            return
        width, height = self._source_size
        required = self._crop_size / min(width, height)
        fit = min(max(self.width(), self._crop_size + 40) / width, max(self.height(), self._crop_size + 40) / height)
        self._scale = max(required, fit)
        self._offset = QPointF(self.width() / 2, self.height() / 2)
        self._resized_cache = None
        self._clamp_offset()

    def _ensure_crop_covered(self) -> None:
        if not self.has_image:
            return
        self._scale = max(self._scale, self._crop_size / min(self._source_size))
        self._resized_cache = None

    def _clamp_offset(self) -> None:
        if not self.has_image:
            return
        scaled_width = self._source_size[0] * self._scale
        scaled_height = self._source_size[1] * self._scale
        cx, cy = self.width() / 2, self.height() / 2
        half = self._crop_size / 2
        min_x = cx + half - scaled_width / 2
        max_x = cx - half + scaled_width / 2
        min_y = cy + half - scaled_height / 2
        max_y = cy - half + scaled_height / 2
        self._offset.setX(min(max(self._offset.x(), min_x), max_x))
        self._offset.setY(min(max(self._offset.y(), min_y), max_y))

    def _zoom(self, direction: int, anchor: QPointF) -> None:
        old_scale = self._scale
        new_scale = max(ZOOM_MIN, min(old_scale * (ZOOM_FACTOR if direction > 0 else 1 / ZOOM_FACTOR), ZOOM_MAX))
        if new_scale == old_scale:
            return
        relative = (anchor - self._offset) / old_scale
        self._scale = new_scale
        self._offset = anchor - relative * new_scale
        self._resized_cache = None
        self._clamp_offset()
        self.update()
        self.changed.emit()
        self.zoomChanged.emit(self._scale)
        if self._notify_change:
            self._notify_change()

    def _crop_rect(self) -> QRectF:
        cx, cy = self.width() / 2, self.height() / 2
        half = self._crop_size / 2
        return QRectF(cx - half, cy - half, self._crop_size, self._crop_size)

    def _display_image(self) -> QImage | None:
        if self._source is None:
            return None
        scaled_size = (max(1, round(self._source.width() * self._scale)), max(1, round(self._source.height() * self._scale)))
        if self._resized_cache is None or self._resized_cache[0] != scaled_size:
            image = self._source.scaled(*scaled_size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._resized_cache = (scaled_size, image)
        return self._resized_cache[1]

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor(THEME.canvas_bg))

        if not self.has_image:
            painter.end()
            return

        image = self._display_image()
        if image is not None:
            target = QRectF(
                self._offset.x() - image.width() / 2,
                self._offset.y() - image.height() / 2,
                image.width(),
                image.height(),
            )
            painter.drawImage(target, image)

        crop = self._crop_rect()
        overlay = QColor(THEME.overlay)
        overlay.setAlpha(150)
        painter.fillRect(QRectF(0, 0, self.width(), crop.top()), overlay)
        painter.fillRect(QRectF(0, crop.bottom(), self.width(), self.height() - crop.bottom()), overlay)
        painter.fillRect(QRectF(0, crop.top(), crop.left(), crop.height()), overlay)
        painter.fillRect(QRectF(crop.right(), crop.top(), self.width() - crop.right(), crop.height()), overlay)

        pen = QPen(THEME.white, 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(crop) if self._round else painter.drawRect(crop)

        guide = QPen(THEME.white, 1)
        guide.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(guide)
        third = crop.width() / 3
        for i in (1, 2):
            x = crop.left() + third * i
            y = crop.top() + third * i
            painter.drawLine(QPointF(x, crop.top()), QPointF(x, crop.bottom()))
            painter.drawLine(QPointF(crop.left(), y), QPointF(crop.right(), y))

        label = "ROUND CROP" if self._round else "SQUARE CROP"
        painter.setPen(QPen(THEME.white))
        font = painter.font()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(int(crop.left() + 10), int(crop.top() - 8), label)
        painter.end()

    def get_cropped_image(self) -> Image.Image:
        if self._pillow_image is None:
            raise RuntimeError("No image imported.")
        crop = self._crop_rect()
        source_x = (crop.left() - self._offset.x() + (self._source_size[0] * self._scale) / 2) / self._scale
        source_y = (crop.top() - self._offset.y() + (self._source_size[1] * self._scale) / 2) / self._scale
        source_size = crop.width() / self._scale
        max_x = max(0.0, self._pillow_image.width - source_size)
        max_y = max(0.0, self._pillow_image.height - source_size)
        source_x = max(0.0, min(source_x, max_x))
        source_y = max(0.0, min(source_y, max_y))
        return self._pillow_image.crop((source_x, source_y, source_x + source_size, source_y + source_size))
