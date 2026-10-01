from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from .config import INVALID_FOLDER_CHARS, OUTPUT_SIZES
from .dxt5 import save_dxt5


class ImageLoadError(ValueError):
    """Raised when an input image cannot be decoded."""


def load_image(path: str | Path) -> Image.Image:
    try:
        with Image.open(path) as image:
            image.load()
            return ImageOps.exif_transpose(image).convert("RGBA")
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageLoadError(f"Could not open the selected image.\n\n{exc}") from exc


def validate_avatar_name(name: str) -> str:
    value = name.strip()
    if not value:
        raise ValueError("Enter an avatar folder name first.")
    if value in {".", ".."} or any(char in INVALID_FOLDER_CHARS for char in value):
        raise ValueError("The avatar folder name contains invalid Windows characters.")
    return value


def apply_round_mask(image: Image.Image) -> Image.Image:
    result = image.convert("RGBA")
    size = result.width
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    result.putalpha(mask)
    return result


def prepare_output(size: int, cropped: Image.Image, round_profile: bool) -> Image.Image:
    result = cropped.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    if round_profile:
        result = apply_round_mask(result)
    return result


def export_avatar(
    *,
    cropped: Image.Image,
    output_parent: str | Path,
    avatar_name: str,
    round_profile: bool,
) -> Path:
    safe_name = validate_avatar_name(avatar_name)
    parent = Path(output_parent)
    output_dir = parent / safe_name
    output_dir.mkdir(parents=True, exist_ok=True)

    avatar_png = prepare_output(440, cropped, round_profile)
    avatar_png.save(output_dir / "avatar.png", format="PNG", optimize=True)

    for filename, size in OUTPUT_SIZES.items():
        save_dxt5(prepare_output(size, cropped, round_profile), output_dir / filename)

    return output_dir
