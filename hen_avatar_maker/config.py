from __future__ import annotations

from dataclasses import dataclass


OUTPUT_SIZES: dict[str, int] = {
    "avatar64.dds": 64,
    "avatar128.dds": 128,
    "avatar260.dds": 260,
    "avatar440.dds": 440,
}

SUPPORTED_IMAGE_FILTER = (
    "Image files (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff);;"
    "PNG (*.png);;"
    "JPEG (*.jpg *.jpeg);;"
    "WEBP (*.webp);;"
    "All files (*)"
)

INVALID_FOLDER_CHARS = set('<>:"/\\|?*')


@dataclass(frozen=True, slots=True)
class Theme:
    bg: str = "#17181c"
    canvas_bg: str = "#101216"
    panel: str = "#292a30"
    panel_alt: str = "#303239"
    border: str = "#3b3e46"
    border_light: str = "#50535d"
    text: str = "#f3f4f6"
    muted: str = "#989da9"
    blue: str = "#4d9af7"
    blue_hover: str = "#5aa3ff"
    blue_pressed: str = "#3f88df"
    white: str = "#ffffff"
    chip: str = "#32343c"
    overlay: str = "#000000"


THEME = Theme()

APP_TITLE = "HEN Avatar Maker"
APP_SUBTITLE = "Create a PS4 HEN avatar from any image."
WINDOW_SIZE = (1024, 720)
WINDOW_MIN_SIZE = (900, 650)
SIDEBAR_WIDTH = 310
CROP_MIN_SIZE = 240
CROP_MAX_SIZE = 500
ZOOM_FACTOR = 1.12
ZOOM_MIN = 0.02
ZOOM_MAX = 20.0
