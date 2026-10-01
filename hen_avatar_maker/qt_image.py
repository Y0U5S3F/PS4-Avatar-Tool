from __future__ import annotations

from PIL import Image
from PyQt6.QtGui import QImage, QPixmap


def pil_to_qimage(image: Image.Image) -> QImage:
    """Return an owning Qt image, independent of Pillow's memory buffer."""
    rgba = image.convert("RGBA")
    width, height = rgba.size
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, width, height, width * 4, QImage.Format.Format_RGBA8888)
    return qimage.copy()


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    """Convert a Pillow RGBA image into a display-friendly QPixmap."""
    return QPixmap.fromImage(pil_to_qimage(image))
