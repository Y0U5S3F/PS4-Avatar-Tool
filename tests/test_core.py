from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from ps4_avatar_tool.dxt5 import encode_dxt5
from ps4_avatar_tool.image_ops import export_avatar, prepare_output, validate_avatar_name


def test_dxt5_header_and_size() -> None:
    image = Image.new("RGBA", (7, 9), (100, 120, 140, 255))
    data = encode_dxt5(image)
    blocks_x = (7 + 3) // 4
    blocks_y = (9 + 3) // 4
    assert data[:4] == b"DDS "
    assert len(data) == 128 + blocks_x * blocks_y * 16


def test_prepare_output_round_mask() -> None:
    image = Image.new("RGBA", (20, 30), (255, 0, 0, 255))
    result = prepare_output(64, image, round_profile=True)
    assert result.size == (64, 64)
    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((32, 32))[3] == 255


def test_avatar_name_validation() -> None:
    assert validate_avatar_name("  CoolAvatar01  ") == "CoolAvatar01"
    for invalid in ("", ".", "..", "a/b", "a\\b", "a:b", "a*b", "avatar<name"):
        try:
            validate_avatar_name(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(invalid)


def test_export_creates_all_assets() -> None:
    image = Image.new("RGBA", (32, 32), (30, 80, 140, 255))
    with TemporaryDirectory() as temp_dir:
        output_dir = export_avatar(
            cropped=image,
            output_parent=Path(temp_dir),
            avatar_name="TestAvatar",
            round_profile=True,
        )
        assert {path.name for path in output_dir.iterdir()} == {
            "avatar.png",
            "avatar64.dds",
            "avatar128.dds",
            "avatar260.dds",
            "avatar440.dds",
        }
