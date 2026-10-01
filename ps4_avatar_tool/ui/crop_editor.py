from __future__ import annotations

from PIL import Image
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QWidget

from ..config import CROP_MAX_SIZE, CROP_MIN_SIZE, THEME, ZOOM_FACTOR, ZOOM_MAX, ZOOM_MIN
from ..qt_image import pil_to_qpixmap


class CropEditor(QWidget):
    """GPU-friendly image viewport with pan, zoom, and a vector crop overlay."""

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
        self.setMinimumSize(1, 1)

        self._pillow_image: Image.Image | None = None
        self._pixmap: QPixmap | None = None
        self._source_size = (0, 0)
        self._scale = 1.0
        self._offset = QPointF()
        self._crop_size = float(CROP_MIN_SIZE)
        self._dragging = False
        self._last_mouse = QPointF()
        self._round = False
        self._initialized = False

    @property
    def has_image(self) -> bool:
        return self._pillow_image is not None and self._pixmap is not None

    def set_image(self, image: Image.Image) -> None:
        self._pillow_image = image.copy().convert("RGBA")
        self._pixmap = pil_to_qpixmap(self._pillow_image)
        self._source_size = (self._pixmap.width(), self._pixmap.height())
        self._update_crop_size()
        self._fit_image()
        self.update()
        self.changed.emit()
        self.zoomChanged.emit(self._scale)

    # ------------------------------------------------------------------
    # Public zoom / rotate API (used by the sidebar buttons)
    # ------------------------------------------------------------------
    @property
    def scale(self) -> float:
        return self._scale

    def min_scale(self) -> float:
        """Smallest allowed zoom: the image must always fully cover the crop frame."""
        if not self.has_image:
            return ZOOM_MIN
        return max(ZOOM_MIN, self._crop_size / min(self._source_size))

    def can_zoom_in(self) -> bool:
        return self.has_image and self._scale < ZOOM_MAX - 1e-9

    def can_zoom_out(self) -> bool:
        return self.has_image and self._scale > self.min_scale() + 1e-9

    def zoom_in(self) -> None:
        if self.has_image:
            self._zoom(1, self._view_center())

    def zoom_out(self) -> None:
        if self.has_image:
            self._zoom(-1, self._view_center())

    def rotate_clockwise(self) -> None:
        """Rotate the image 90 degrees clockwise, keeping the same area inside the crop."""
        if self._pillow_image is None:
            return
        center = self._view_center()
        to_crop = center - self._offset  # image centre -> crop centre
        rotated = QPointF(-to_crop.y(), to_crop.x())  # same vector after a 90° CW turn

        self._pillow_image = self._pillow_image.transpose(Image.Transpose.ROTATE_270)
        self._pixmap = pil_to_qpixmap(self._pillow_image)
        self._source_size = (self._pixmap.width(), self._pixmap.height())

        self._offset = center - rotated
        self._ensure_crop_covered()
        self._clamp_offset()
        self.update()
        self.changed.emit()
        self.zoomChanged.emit(self._scale)

    def _view_center(self) -> QPointF:
        return QPointF(self.width() / 2.0, self.height() / 2.0)

    def set_round(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if self._round == enabled:
            return
        self._round = enabled
        self.update()
        self.changed.emit()

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._update_crop_size()
        if self.has_image:
            old_scale = self._scale
            self._ensure_crop_covered()
            self._clamp_offset()
            if abs(self._scale - old_scale) > 1e-9:
                self.zoomChanged.emit(self._scale)
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
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setCursor(Qt.CursorShape.CrossCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802
        if not self.has_image:
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        self._zoom(1 if delta > 0 else -1, event.position())
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
        available = min(max(self.width() - 60, CROP_MIN_SIZE), max(self.height() - 60, CROP_MIN_SIZE))
        self._crop_size = float(max(CROP_MIN_SIZE, min(CROP_MAX_SIZE, available)))

    def _fit_image(self) -> None:
        if not self.has_image:
            return
        width, height = self._source_size
        if width <= 0 or height <= 0:
            return
        required = self._crop_size / min(width, height)
        fit = min(max(self.width(), int(self._crop_size) + 40) / width, max(self.height(), int(self._crop_size) + 40) / height)
        self._scale = max(required, fit)
        self._offset = QPointF(self.width() / 2.0, self.height() / 2.0)
        self._clamp_offset()
        self._initialized = True

    def _ensure_crop_covered(self) -> None:
        if not self.has_image:
            return
        self._scale = max(self._scale, self.min_scale())

    def _clamp_offset(self) -> None:
        if not self.has_image:
            return
        width = self._source_size[0] * self._scale
        height = self._source_size[1] * self._scale
        cx, cy = self.width() / 2.0, self.height() / 2.0
        half = self._crop_size / 2.0
        min_x = cx + half - width / 2.0
        max_x = cx - half + width / 2.0
        min_y = cy + half - height / 2.0
        max_y = cy - half + height / 2.0
        self._offset.setX(min(max(self._offset.x(), min_x), max_x))
        self._offset.setY(min(max(self._offset.y(), min_y), max_y))

    def _zoom(self, direction: int, anchor: QPointF) -> None:
        old_scale = self._scale
        factor = ZOOM_FACTOR if direction > 0 else 1.0 / ZOOM_FACTOR
        new_scale = max(self.min_scale(), min(ZOOM_MAX, old_scale * factor))
        if abs(new_scale - old_scale) < 1e-9:
            return

        relative = (anchor - self._offset) / old_scale
        self._scale = new_scale
        self._offset = anchor - relative * new_scale
        self._clamp_offset()
        self.update()
        self.changed.emit()
        self.zoomChanged.emit(self._scale)

    def _crop_rect(self) -> QRectF:
        cx, cy = self.width() / 2.0, self.height() / 2.0
        half = self._crop_size / 2.0
        return QRectF(cx - half, cy - half, self._crop_size, self._crop_size)

    def _paint_overlay(self, painter: QPainter, crop: QRectF) -> None:
        overlay = QColor(THEME.overlay)
        overlay.setAlpha(155)

        if self._round:
            # Dark overlay with a circular hole (even-odd fill). Nothing is erased
            # from the widget, so the image underneath stays untouched.
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.OddEvenFill)
            path.addRect(QRectF(self.rect()))
            path.addEllipse(crop)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.fillPath(path, overlay)
        else:
            left = crop.left()
            top = crop.top()
            right = crop.right()
            bottom = crop.bottom()
            painter.fillRect(0, 0, self.width(), max(0, int(top)), overlay)
            painter.fillRect(0, int(bottom), self.width(), max(0, self.height() - int(bottom)), overlay)
            painter.fillRect(0, int(top), max(0, int(left)), max(0, int(crop.height())), overlay)
            painter.fillRect(int(right), int(top), max(0, self.width() - int(right)), max(0, int(crop.height())), overlay)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter()
        if not painter.begin(self):
            painter.dispose()
            return
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.fillRect(self.rect(), QColor(THEME.canvas_bg))

            if not self.has_image:
                return

            assert self._pixmap is not None
            painter.save()
            try:
                painter.translate(self._offset)
                painter.scale(self._scale, self._scale)
                painter.drawPixmap(
                    QPointF(-self._pixmap.width() / 2.0, -self._pixmap.height() / 2.0),
                    self._pixmap,
                )
            finally:
                painter.restore()

            crop = self._crop_rect()
            self._paint_overlay(painter, crop)

            crop_pen = QPen(QColor(THEME.white))
            crop_pen.setWidthF(1.5)
            painter.setPen(crop_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if self._round:
                painter.drawEllipse(crop)
            else:
                painter.drawRect(crop)

            painter.save()
            try:
                clip = QPainterPath()
                if self._round:
                    clip.addEllipse(crop)
                else:
                    clip.addRect(crop)
                painter.setClipPath(clip)

                guide_pen = QPen(QColor(THEME.white))
                guide_pen.setWidthF(1.0)
                guide_pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(guide_pen)
                third = crop.width() / 3.0
                for index in (1, 2):
                    x = crop.left() + third * index
                    y = crop.top() + third * index
                    painter.drawLine(QPointF(x, crop.top()), QPointF(x, crop.bottom()))
                    painter.drawLine(QPointF(crop.left(), y), QPointF(crop.right(), y))
            finally:
                painter.restore()

            label = "ROUND CROP" if self._round else "SQUARE CROP"
            label_font = painter.font()
            label_font.setPointSize(8)
            label_font.setBold(True)
            painter.setFont(label_font)
            painter.setPen(QColor(THEME.white))
            painter.drawText(QPointF(crop.left() + 10, max(14.0, crop.top() - 8)), label)
        finally:
            if painter.isActive():
                painter.end()

    def get_cropped_image(self) -> Image.Image:
        if self._pillow_image is None:
            raise RuntimeError("No image imported.")

        crop = self._crop_rect()
        source_width, source_height = self._source_size
        if source_width <= 0 or source_height <= 0 or self._scale <= 0:
            raise RuntimeError("The crop editor is not initialized.")

        source_x = (
            crop.left() - self._offset.x() + (source_width * self._scale) / 2.0
        ) / self._scale
        source_y = (
            crop.top() - self._offset.y() + (source_height * self._scale) / 2.0
        ) / self._scale
        source_size = crop.width() / self._scale

        max_x = max(0.0, self._pillow_image.width - source_size)
        max_y = max(0.0, self._pillow_image.height - source_size)
        source_x = max(0.0, min(source_x, max_x))
        source_y = max(0.0, min(source_y, max_y))

        return self._pillow_image.crop((source_x, source_y, source_x + source_size, source_y + source_size))
