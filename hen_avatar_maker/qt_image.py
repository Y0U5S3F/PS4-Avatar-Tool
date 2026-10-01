from __future__ import annotations

from PIL import Image
from PyQt6.QtGui import QImage


def pil_to_qimage(image: Image.Image) -> QImage:
    """Create an owning QImage from a Pillow RGBA image."""
    rgba = image.convert("RGBA")
    width, height = rgba.size
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, width, height, width * 4, QImage.Format.Format_RGBA8888)
    return qimage.copy()
