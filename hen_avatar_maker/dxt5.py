from __future__ import annotations

import struct
from pathlib import Path

from PIL import Image


def _rgb565_from_rgb(r: int, g: int, b: int) -> int:
    return (
        ((r * 31 + 127) // 255 << 11)
        | ((g * 63 + 127) // 255 << 5)
        | ((b * 31 + 127) // 255)
    )


def _rgb_from_565(value: int) -> tuple[int, int, int]:
    return (
        ((value >> 11) & 0x1F) * 255 // 31,
        ((value >> 5) & 0x3F) * 255 // 63,
        (value & 0x1F) * 255 // 31,
    )


def _color_palette(c0: int, c1: int) -> list[tuple[int, int, int]]:
    a = _rgb_from_565(c0)
    b = _rgb_from_565(c1)
    return [
        a,
        b,
        (
            (2 * a[0] + b[0]) // 3,
            (2 * a[1] + b[1]) // 3,
            (2 * a[2] + b[2]) // 3,
        ),
        (
            (a[0] + 2 * b[0]) // 3,
            (a[1] + 2 * b[1]) // 3,
            (a[2] + 2 * b[2]) // 3,
        ),
    ]


def _choose_color_endpoints(
    pixels: list[tuple[int, int, int, int]],
) -> tuple[int, int]:
    rs = [pixel[0] for pixel in pixels]
    gs = [pixel[1] for pixel in pixels]
    bs = [pixel[2] for pixel in pixels]

    min_rgb = (min(rs), min(gs), min(bs))
    max_rgb = (max(rs), max(gs), max(bs))

    c0 = _rgb565_from_rgb(*max_rgb)
    c1 = _rgb565_from_rgb(*min_rgb)
    if c0 == c1:
        if c0 > 0:
            c1 = c0 - 1
        else:
            c0 = 1
    return c0, c1


def _encode_color_block(pixels: list[tuple[int, int, int, int]]) -> bytes:
    c0, c1 = _choose_color_endpoints(pixels)
    palette = _color_palette(c0, c1)

    indices: list[int] = []
    for r, g, b, _alpha in pixels:
        best_index = min(
            range(4),
            key=lambda index: (
                (r - palette[index][0]) ** 2
                + (g - palette[index][1]) ** 2
                + (b - palette[index][2]) ** 2
            ),
        )
        indices.append(best_index)

    packed = 0
    for index_position, index in enumerate(indices):
        packed |= (index & 0x3) << (2 * index_position)

    return struct.pack("<HHI", c0, c1, packed)


def _alpha_palette(a0: int, a1: int) -> list[int]:
    if a0 > a1:
        return [
            a0,
            a1,
            (6 * a0 + a1) // 7,
            (5 * a0 + 2 * a1) // 7,
            (4 * a0 + 3 * a1) // 7,
            (3 * a0 + 4 * a1) // 7,
            (2 * a0 + 5 * a1) // 7,
            (a0 + 6 * a1) // 7,
        ]

    return [
        a0,
        a1,
        (4 * a0 + a1) // 5,
        (3 * a0 + 2 * a1) // 5,
        (2 * a0 + 3 * a1) // 5,
        (a0 + 4 * a1) // 5,
        0,
        255,
    ]


def _encode_alpha_block(pixels: list[tuple[int, int, int, int]]) -> bytes:
    alphas = [pixel[3] for pixel in pixels]
    low = min(alphas)
    high = max(alphas)

    if low == high:
        if high < 255:
            a0, a1 = high + 1, low
        else:
            a0, a1 = 255, 254
    else:
        a0, a1 = high, low

    palette = _alpha_palette(a0, a1)
    indices: list[int] = []
    for alpha in alphas:
        best_index = min(
            range(8),
            key=lambda index: (alpha - palette[index]) ** 2,
        )
        indices.append(best_index)

    packed = 0
    for index_position, index in enumerate(indices):
        packed |= (index & 0x7) << (3 * index_position)

    return bytes((a0, a1)) + packed.to_bytes(6, "little")


def encode_dxt5(image: Image.Image) -> bytes:
    """Return a complete DDS file containing one DXT5 mip level."""
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    encoded = bytearray()

    for block_y in range(0, height, 4):
        for block_x in range(0, width, 4):
            block: list[tuple[int, int, int, int]] = []
            for y in range(4):
                source_y = min(block_y + y, height - 1)
                for x in range(4):
                    source_x = min(block_x + x, width - 1)
                    block.append(pixels[source_x, source_y])

            encoded += _encode_alpha_block(block)
            encoded += _encode_color_block(block)

    pixel_format = struct.pack(
        "<II4s5I",
        32,
        0x00000004,
        b"DXT5",
        0,
        0,
        0,
        0,
        0,
    )

    header = bytearray(b"DDS ")
    header += struct.pack(
        "<I6I",
        124,
        0x00081007,
        height,
        width,
        ((width + 3) // 4) * 16,
        0,
        1,
    )
    header += struct.pack("<11I", *([0] * 11))
    header += pixel_format
    header += struct.pack("<5I", 0x1000, 0, 0, 0, 0)

    if len(header) != 128:
        raise AssertionError("DDS header must be exactly 128 bytes")

    return bytes(header) + bytes(encoded)


def save_dxt5(image: Image.Image, path: Path) -> None:
    path.write_bytes(encode_dxt5(image))
