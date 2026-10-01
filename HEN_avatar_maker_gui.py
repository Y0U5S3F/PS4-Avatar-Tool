#!/usr/bin/env python3
"""
HEN Avatar Maker GUI

Create PS4 HEN custom-avatar files from any image.

Features:
- Modern dark UI with a focused square crop canvas.
- Import Image button.
- Drag to reposition and mouse-wheel to zoom.
- Square / Round profile picture mode.
- Export To... folder picker.
- Output chips showing generated files.
- Pure-Python DXT5 DDS encoder (no ImageMagick required).

Requires:
    Pillow
"""

from __future__ import annotations

import struct
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageOps, ImageTk, UnidentifiedImageError


OUTPUT_SIZES = {
    "avatar64.dds": 64,
    "avatar128.dds": 128,
    "avatar260.dds": 260,
    "avatar440.dds": 440,
}

SUPPORTED_IMAGE_TYPES = [
    ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff"),
    ("PNG", "*.png"),
    ("JPEG", "*.jpg *.jpeg"),
    ("WEBP", "*.webp"),
    ("All files", "*.*"),
]


# ---------------------------------------------------------------------------
# Pure-Python DXT5 encoder
# ---------------------------------------------------------------------------


def _rgb565_from_rgb(r: int, g: int, b: int) -> int:
    return (
        ((r * 31 + 127) // 255 << 11)
        | ((g * 63 + 127) // 255 << 5)
        | ((b * 31 + 127) // 255)
    )


def _rgb_from_565(value: int) -> tuple[int, int, int]:
    r = ((value >> 11) & 0x1F) * 255 // 31
    g = ((value >> 5) & 0x3F) * 255 // 63
    b = (value & 0x1F) * 255 // 31
    return r, g, b


def _color_palette(c0: int, c1: int) -> list[tuple[int, int, int]]:
    a = _rgb_from_565(c0)
    b = _rgb_from_565(c1)
    return [
        a,
        b,
        ((2 * a[0] + b[0]) // 3, (2 * a[1] + b[1]) // 3, (2 * a[2] + b[2]) // 3),
        ((a[0] + 2 * b[0]) // 3, (a[1] + 2 * b[1]) // 3, (a[2] + 2 * b[2]) // 3),
    ]


def _choose_color_endpoints(pixels: list[tuple[int, int, int, int]]) -> tuple[int, int]:
    rs = [p[0] for p in pixels]
    gs = [p[1] for p in pixels]
    bs = [p[2] for p in pixels]

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

    indices = []
    for r, g, b, _a in pixels:
        best = min(
            range(4),
            key=lambda i: (
                (r - palette[i][0]) ** 2
                + (g - palette[i][1]) ** 2
                + (b - palette[i][2]) ** 2
            ),
        )
        indices.append(best)

    packed = 0
    for i, index in enumerate(indices):
        packed |= (index & 0x3) << (2 * i)

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
    alphas = [p[3] for p in pixels]
    lo = min(alphas)
    hi = max(alphas)

    if lo == hi:
        if hi < 255:
            a0, a1 = hi + 1, lo
        else:
            a0, a1 = 255, 254
    else:
        a0, a1 = hi, lo

    palette = _alpha_palette(a0, a1)

    indices = []
    for alpha in alphas:
        best = min(range(8), key=lambda i: (alpha - palette[i]) ** 2)
        indices.append(best)

    packed = 0
    for i, index in enumerate(indices):
        packed |= (index & 0x7) << (3 * i)

    return bytes((a0, a1)) + packed.to_bytes(6, "little")


def encode_dxt5(image: Image.Image) -> bytes:
    """Return a complete DDS file containing one DXT5 mip level."""
    image = image.convert("RGBA")
    width, height = image.size
    pixels = image.load()
    encoded = bytearray()

    for by in range(0, height, 4):
        for bx in range(0, width, 4):
            block: list[tuple[int, int, int, int]] = []
            for y in range(4):
                sy = min(by + y, height - 1)
                for x in range(4):
                    sx = min(bx + x, width - 1)
                    block.append(pixels[sx, sy])

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

    assert len(header) == 128
    return bytes(header) + bytes(encoded)


def save_dxt5(image: Image.Image, path: Path) -> None:
    path.write_bytes(encode_dxt5(image))


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------


class AvatarMakerApp(tk.Tk):
    BG = "#18191D"
    PANEL = "#202228"
    PANEL_2 = "#252831"
    CANVAS_BG = "#111318"
    BORDER = "#343842"
    BORDER_LIGHT = "#444954"
    TEXT = "#F4F5F7"
    MUTED = "#969BA8"
    BLUE = "#4B8CF8"
    BLUE_HOVER = "#5A96FA"
    BLUE_PRESSED = "#3F7EE4"
    CHIP_BG = "#2B2F38"
    SUCCESS = "#66D19E"

    def __init__(self) -> None:
        super().__init__()
        self.title("HEN Avatar Maker")
        self.geometry("900x640")
        self.minsize(820, 590)
        self.configure(bg=self.BG)

        self.source_image: Image.Image | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.image_scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.crop_size = 430
        self.dragging = False
        self.last_mouse = (0, 0)

        self.avatar_name = tk.StringVar(value="MyAvatar")
        self.export_dir = tk.StringVar(value="Choose a folder")
        self.is_round = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Import an image to begin")

        self._configure_styles()
        self._build_ui()
        self.after(120, self._initial_canvas_setup)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=self.BG)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("Section.TFrame", background=self.PANEL)
        style.configure(
            "Title.TLabel",
            background=self.BG,
            foreground=self.TEXT,
            font=("Segoe UI", 21, "bold"),
        )
        style.configure(
            "Sub.TLabel",
            background=self.BG,
            foreground=self.MUTED,
            font=("Segoe UI", 9),
        )
        style.configure(
            "PanelTitle.TLabel",
            background=self.PANEL,
            foreground=self.TEXT,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "PanelLabel.TLabel",
            background=self.PANEL,
            foreground=self.TEXT,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Tiny.TLabel",
            background=self.PANEL,
            foreground=self.MUTED,
            font=("Segoe UI", 8),
        )
        style.configure(
            "TEntry",
            fieldbackground=self.PANEL_2,
            background=self.PANEL_2,
            foreground=self.TEXT,
            insertcolor=self.TEXT,
            bordercolor=self.BORDER,
            lightcolor=self.BORDER,
            darkcolor=self.BORDER,
            padding=(10, 8),
            font=("Segoe UI", 9),
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", self.BLUE)],
            lightcolor=[("focus", self.BLUE)],
            darkcolor=[("focus", self.BLUE)],
        )
        style.configure(
            "Modern.TCheckbutton",
            background=self.PANEL,
            foreground=self.TEXT,
            font=("Segoe UI", 9),
            padding=0,
        )
        style.map(
            "Modern.TCheckbutton",
            background=[("active", self.PANEL)],
            foreground=[("active", self.TEXT)],
        )

    def _make_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        *,
        primary: bool = False,
    ) -> tk.Button:
        bg = self.BLUE if primary else self.PANEL_2
        active = self.BLUE_HOVER if primary else self.BORDER_LIGHT
        pressed = self.BLUE_PRESSED if primary else self.BORDER

        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=self.TEXT,
            activebackground=active,
            activeforeground=self.TEXT,
            disabledforeground="#686D78",
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            padx=12,
            pady=9,
        )

        def on_enter(_event) -> None:
            if str(button["state"]) != "disabled":
                button.configure(bg=active)

        def on_leave(_event) -> None:
            button.configure(bg=bg)

        def on_press(_event) -> None:
            if str(button["state"]) != "disabled":
                button.configure(bg=pressed)

        def on_release(_event) -> None:
            if str(button["state"]) != "disabled":
                button.configure(bg=active)

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        button.bind("<ButtonPress-1>", on_press)
        button.bind("<ButtonRelease-1>", on_release)
        return button

    def _build_ui(self) -> None:
        shell = tk.Frame(self, bg=self.BG)
        shell.pack(fill="both", expand=True, padx=22, pady=20)

        header = tk.Frame(shell, bg=self.BG)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text="HEN Avatar Maker", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Create a PS4 HEN avatar from any image.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(shell, bg=self.BG)
        content.pack(fill="both", expand=True)

        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0)
        content.grid_rowconfigure(0, weight=1)

        # Main canvas area.
        canvas_wrap = tk.Frame(
            content,
            bg=self.CANVAS_BG,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )
        canvas_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        self.canvas = tk.Canvas(
            canvas_wrap,
            bg=self.CANVAS_BG,
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True, padx=1, pady=1)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._zoom(+1, e.x, e.y))
        self.canvas.bind("<Button-5>", lambda e: self._zoom(-1, e.x, e.y))

        # Sidebar.
        sidebar = tk.Frame(
            content,
            bg=self.PANEL,
            highlightbackground=self.BORDER,
            highlightthickness=1,
            width=265,
        )
        sidebar.grid(row=0, column=1, sticky="ns")
        sidebar.pack_propagate(False)

        body = tk.Frame(sidebar, bg=self.PANEL)
        body.pack(fill="both", expand=True, padx=18, pady=18)

        ttk.Label(body, text="CONTROLS", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(
            body,
            text="Crop, Shape, then Export.",
            style="Tiny.TLabel",
        ).pack(anchor="w", pady=(3, 16))

        import_button = self._make_button(body, "Import Image", self.import_image)
        import_button.pack(fill="x", pady=(0, 14))

        ttk.Separator(body).pack(fill="x", pady=(0, 15))

        ttk.Label(body, text="Profile picture", style="PanelLabel.TLabel").pack(anchor="w")

        shape_row = tk.Frame(body, bg=self.PANEL)
        shape_row.pack(fill="x", pady=(8, 4))
        shape_check = ttk.Checkbutton(
            shape_row,
            text="Round profile picture",
            variable=self.is_round,
            style="Modern.TCheckbutton",
            command=self._on_shape_changed,
        ).pack(anchor="w", pady=(3, 16))

        ttk.Label(body, text="Avatar folder name", style="PanelLabel.TLabel").pack(anchor="w")
        ttk.Entry(body, textvariable=self.avatar_name).pack(fill="x", pady=(7, 14))

        ttk.Label(body, text="Export location", style="PanelLabel.TLabel").pack(anchor="w")
        location = ttk.Entry(body, textvariable=self.export_dir, state="readonly")
        location.pack(fill="x", pady=(7, 5))
        ttk.Label(
            body,
            text="A folder with the avatar name will be created here.",
            style="Tiny.TLabel",
            wraplength=225,
        ).pack(anchor="w", pady=(0, 12))

        self._make_button(body, "Export To...", self.export_avatar, primary=True).pack(fill="x")

        ttk.Separator(body).pack(fill="x", pady=(18, 14))

        ttk.Label(body, text="OUTPUT", style="PanelTitle.TLabel").pack(anchor="w")
        chip_frame = tk.Frame(body, bg=self.PANEL)
        chip_frame.pack(fill="x", pady=(9, 0))

        for name in ["avatar.png", "avatar64.dds", "avatar128.dds", "avatar260.dds", "avatar440.dds"]:
            self._make_chip(chip_frame, name)

        footer = tk.Frame(shell, bg=self.BG)
        footer.pack(fill="x", pady=(11, 0))
        self.status_label = ttk.Label(footer, textvariable=self.status, style="Sub.TLabel")
        self.status_label.pack(anchor="w")

    def _make_chip(self, parent: tk.Widget, text: str) -> None:
        chip = tk.Label(
            parent,
            text=text,
            bg=self.CHIP_BG,
            fg=self.TEXT,
            font=("Segoe UI", 8),
            padx=8,
            pady=4,
        )
        chip.pack(side="left", padx=(0, 5), pady=(0, 5))

    def _initial_canvas_setup(self) -> None:
        self._update_crop_size()
        self._draw()

    def _on_canvas_resize(self, _event: tk.Event) -> None:
        old_size = self.crop_size
        self._update_crop_size()
        if old_size != self.crop_size and self.source_image is not None:
            self._fit_image()
        self._draw()

    def _update_crop_size(self) -> None:
        w = max(self.canvas.winfo_width(), 1)
        h = max(self.canvas.winfo_height(), 1)
        self.crop_size = max(230, min(470, min(w - 50, h - 50)))

    def import_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Import image",
            filetypes=SUPPORTED_IMAGE_TYPES,
        )
        if not path:
            return

        try:
            with Image.open(path) as image:
                image.load()
                self.source_image = ImageOps.exif_transpose(image).convert("RGBA")
        except (UnidentifiedImageError, OSError) as exc:
            messagebox.showerror("Import failed", f"Could not open the selected image.\n\n{exc}")
            return

        image_name = Path(path).name
        self.status.set(f"Loaded {image_name}  •  {self.source_image.width}×{self.source_image.height}")
        self._fit_image()
        self._draw()

    def _fit_image(self) -> None:
        if self.source_image is None:
            return

        w, h = self.source_image.size
        required = self.crop_size / min(w, h)
        canvas_w = max(self.canvas.winfo_width(), self.crop_size + 20)
        canvas_h = max(self.canvas.winfo_height(), self.crop_size + 20)
        fit = min(canvas_w / w, canvas_h / h)
        self.image_scale = max(required, fit)

        self.offset_x = self.canvas.winfo_width() / 2
        self.offset_y = self.canvas.winfo_height() / 2
        self._clamp_offset()

    def _crop_box(self) -> tuple[float, float, float, float]:
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        half = self.crop_size / 2
        return cx - half, cy - half, cx + half, cy + half

    def _scaled_size(self) -> tuple[int, int]:
        assert self.source_image is not None
        return (
            max(1, round(self.source_image.width * self.image_scale)),
            max(1, round(self.source_image.height * self.image_scale)),
        )

    def _clamp_offset(self) -> None:
        if self.source_image is None:
            return

        sw, sh = self._scaled_size()
        half_crop = self.crop_size / 2
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        cx = cw / 2
        cy = ch / 2

        min_x = cx + half_crop - sw / 2
        max_x = cx - half_crop + sw / 2
        min_y = cy + half_crop - sh / 2
        max_y = cy - half_crop + sh / 2

        self.offset_x = min(max(self.offset_x, min_x), max_x)
        self.offset_y = min(max(self.offset_y, min_y), max_y)

    def _zoom(self, direction: int, mouse_x: float, mouse_y: float) -> None:
        if self.source_image is None:
            return

        old_scale = self.image_scale
        factor = 1.12 if direction > 0 else 1 / 1.12
        new_scale = max(0.01, min(old_scale * factor, 20.0))

        rel_x = (mouse_x - self.offset_x) / old_scale
        rel_y = (mouse_y - self.offset_y) / old_scale
        self.image_scale = new_scale
        self.offset_x = mouse_x - rel_x * new_scale
        self.offset_y = mouse_y - rel_y * new_scale
        self._clamp_offset()
        self._draw()
        self.status.set(f"Zoom {self.image_scale:.2f}×  •  Drag to reposition")

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        self._zoom(1 if event.delta > 0 else -1, event.x, event.y)

    def _on_mouse_down(self, event: tk.Event) -> None:
        if self.source_image is None:
            return
        self.dragging = True
        self.last_mouse = (event.x, event.y)
        self.canvas.configure(cursor="fleur")

    def _on_mouse_drag(self, event: tk.Event) -> None:
        if not self.dragging or self.source_image is None:
            return
        last_x, last_y = self.last_mouse
        self.offset_x += event.x - last_x
        self.offset_y += event.y - last_y
        self.last_mouse = (event.x, event.y)
        self._clamp_offset()
        self._draw()

    def _on_mouse_up(self, _event: tk.Event) -> None:
        self.dragging = False
        self.canvas.configure(cursor="crosshair")

    def _on_shape_changed(self) -> None:
        self._draw()
        mode = "Round" if self.is_round.get() else "Square"
        self.status.set(f"{mode} profile picture mode selected")

    def _draw_empty_state(self, w: int, h: int) -> None:
        margin = 32
        self.canvas.create_rectangle(
            margin,
            margin,
            w - margin,
            h - margin,
            outline=self.BORDER_LIGHT,
            width=1,
            dash=(7, 7),
        )
        self.canvas.create_text(
            w / 2,
            h / 2 - 16,
            text="Import an image",
            fill=self.TEXT,
            font=("Segoe UI", 15, "bold"),
        )
        self.canvas.create_text(
            w / 2,
            h / 2 + 13,
            text="Choose a square area, then drag and zoom to frame it",
            fill=self.MUTED,
            font=("Segoe UI", 9),
        )

    def _draw(self) -> None:
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w < 2 or h < 2:
            return

        if self.source_image is None:
            self._draw_empty_state(w, h)
            return

        sw, sh = self._scaled_size()
        display = self.source_image.resize((sw, sh), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(display)
        self.canvas.create_image(self.offset_x, self.offset_y, image=self.preview_photo)

        x1, y1, x2, y2 = self._crop_box()

        # Dim everything outside the square crop.
        self.canvas.create_rectangle(0, 0, w, y1, fill="#000000", outline="")
        self.canvas.create_rectangle(0, y2, w, h, fill="#000000", outline="")
        self.canvas.create_rectangle(0, y1, x1, y2, fill="#000000", outline="")
        self.canvas.create_rectangle(x2, y1, w, y2, fill="#000000", outline="")

        if self.is_round.get():
            self.canvas.create_oval(x1, y1, x2, y2, outline="#FFFFFF", width=2)
            label = "ROUND CROP"
        else:
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="#FFFFFF", width=2)
            label = "SQUARE CROP"

        third = self.crop_size / 3
        line_fill = "#FFFFFF"
        guide_kw = {"fill": line_fill, "width": 1, "dash": (4, 6)}
        for i in (1, 2):
            x = x1 + third * i
            y = y1 + third * i
            self.canvas.create_line(x, y1, x, y2, **guide_kw)
            self.canvas.create_line(x1, y, x2, y, **guide_kw)

        self.canvas.create_text(
            x1 + 10,
            y1 - 9,
            text=label,
            anchor="w",
            fill="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
        )

    def _get_cropped_image(self) -> Image.Image:
        if self.source_image is None:
            raise RuntimeError("No image imported.")

        x1, y1, x2, y2 = self._crop_box()
        crop_w = x2 - x1

        sx1 = (x1 - self.offset_x + (self.source_image.width * self.image_scale) / 2) / self.image_scale
        sy1 = (y1 - self.offset_y + (self.source_image.height * self.image_scale) / 2) / self.image_scale
        source_crop = crop_w / self.image_scale

        max_x = max(0.0, self.source_image.width - source_crop)
        max_y = max(0.0, self.source_image.height - source_crop)
        sx1 = max(0.0, min(sx1, max_x))
        sy1 = max(0.0, min(sy1, max_y))

        return self.source_image.crop((sx1, sy1, sx1 + source_crop, sy1 + source_crop))

    def _apply_round_mask(self, image: Image.Image) -> Image.Image:
        image = image.convert("RGBA")
        size = image.width
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size - 1, size - 1), fill=255)
        image.putalpha(mask)
        return image

    def _prepare_output(self, size: int, cropped: Image.Image) -> Image.Image:
        result = cropped.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
        if self.is_round.get():
            result = self._apply_round_mask(result)
        return result

    def export_avatar(self) -> None:
        if self.source_image is None:
            messagebox.showwarning("No image", "Import an image before exporting.")
            return

        name = self.avatar_name.get().strip()
        if not name:
            messagebox.showwarning("Missing folder name", "Enter an avatar folder name first.")
            return

        invalid = set('<>:"/\\|?*')
        if any(ch in invalid for ch in name) or name in {".", ".."}:
            messagebox.showwarning(
                "Invalid folder name",
                "The avatar folder name contains invalid Windows characters.",
            )
            return

        selected = filedialog.askdirectory(title="Choose export location")
        if not selected:
            return

        parent = Path(selected)
        output_dir = parent / name

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            cropped = self._get_cropped_image()

            avatar_440 = self._prepare_output(440, cropped)
            avatar_440.save(output_dir / "avatar.png", format="PNG", optimize=True)

            for filename, size in OUTPUT_SIZES.items():
                resized = self._prepare_output(size, cropped)
                save_dxt5(resized, output_dir / filename)

        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Export failed", f"Could not create the avatar files.\n\n{exc}")
            return

        self.export_dir.set(str(parent))
        shape = "round" if self.is_round.get() else "square"
        self.status.set(f"Exported {shape} avatar to {output_dir}")
        messagebox.showinfo(
            "Export complete",
            f"Your {shape} avatar files are ready.\n\n{output_dir}",
        )


def main() -> None:
    app = AvatarMakerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
