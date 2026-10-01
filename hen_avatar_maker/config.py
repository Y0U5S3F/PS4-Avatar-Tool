from __future__ import annotations

from dataclasses import dataclass


OUTPUT_SIZES: dict[str, int] = {
    "avatar64.dds": 64,
    "avatar128.dds": 128,
    "avatar260.dds": 260,
    "avatar440.dds": 440,
}

OUTPUT_PREVIEW_NAMES: tuple[str, ...] = (
    "avatar.png",
    *OUTPUT_SIZES.keys(),
)

SUPPORTED_IMAGE_TYPES: list[tuple[str, str]] = [
    ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff"),
    ("PNG", "*.png"),
    ("JPEG", "*.jpg *.jpeg"),
    ("WEBP", "*.webp"),
    ("All files", "*.*"),
]

INVALID_FOLDER_CHARS = set('<>:"/\\|?*')


@dataclass(frozen=True, slots=True)
class Theme:
    bg: str = "#18191d"
    canvas_bg: str = "#101216"
    panel: str = "#25262b"
    panel_alt: str = "#2d2f35"
    panel_border: str = "#3a3d45"
    panel_border_light: str = "#4a4d55"
    text: str = "#f4f5f7"
    muted: str = "#9a9ea9"
    blue: str = "#4d9af7"
    blue_hover: str = "#5ca3fb"
    blue_pressed: str = "#3d86dc"
    chip_bg: str = "#30323a"
    chip_border: str = "#3e414a"
    overlay: str = "#000000"
    white: str = "#ffffff"
    success: str = "#66d19e"
    danger: str = "#e56b78"


THEME = Theme()

APP_TITLE = "HEN Avatar Maker"
APP_SUBTITLE = "Create a PS4 HEN avatar from any image."
WINDOW_SIZE = "1020x740"
WINDOW_MIN_SIZE = (900, 650)
SIDEBAR_WIDTH = 282
CROP_MIN_SIZE = 220
CROP_MAX_SIZE = 500
ZOOM_FACTOR = 1.12
ZOOM_MIN = 0.01
ZOOM_MAX = 20.0
