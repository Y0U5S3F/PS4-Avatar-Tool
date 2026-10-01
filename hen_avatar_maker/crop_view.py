from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from PIL import Image, ImageTk

from .config import CROP_MAX_SIZE, CROP_MIN_SIZE, THEME, ZOOM_FACTOR, ZOOM_MAX, ZOOM_MIN


class CropView(tk.Canvas):
    """Interactive pan/zoom square crop editor."""

    def __init__(self, master: tk.Misc, *, round_variable: tk.BooleanVar, on_status: Callable[[str], None], on_change: Callable[[], None] | None = None) -> None:
        super().__init__(
            master,
            bg=THEME.canvas_bg,
            highlightthickness=0,
            bd=0,
            cursor="crosshair",
        )
        self.round_variable = round_variable
        self.on_status = on_status
        self.on_change = on_change
        self.source_image: Image.Image | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.image_scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.crop_size = 430
        self.dragging = False
        self.last_mouse = (0, 0)

        self.bind("<Configure>", self._on_resize)
        self.bind("<ButtonPress-1>", self._on_mouse_down)
        self.bind("<B1-Motion>", self._on_mouse_drag)
        self.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.bind("<MouseWheel>", self._on_mouse_wheel)
        self.bind("<Button-4>", lambda event: self._zoom(+1, event.x, event.y))
        self.bind("<Button-5>", lambda event: self._zoom(-1, event.x, event.y))

        self.after_idle(self.redraw)

    def set_image(self, image: Image.Image) -> None:
        self.source_image = image.copy().convert("RGBA")
        self._fit_image()
        self.redraw()
        self._notify_change()

    def set_round_mode(self) -> None:
        self.redraw()
        self._notify_change()

    def _notify_change(self) -> None:
        if self.on_change is not None:
            self.on_change()

    def _on_resize(self, _event: tk.Event) -> None:
        old_size = self.crop_size
        self._update_crop_size()
        if old_size != self.crop_size and self.source_image is not None:
            self._fit_image()
        self.redraw()

    def _update_crop_size(self) -> None:
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        self.crop_size = max(CROP_MIN_SIZE, min(CROP_MAX_SIZE, min(width - 64, height - 64)))

    def _fit_image(self) -> None:
        if self.source_image is None:
            return

        width, height = self.source_image.size
        required = self.crop_size / min(width, height)
        canvas_width = max(self.winfo_width(), self.crop_size + 20)
        canvas_height = max(self.winfo_height(), self.crop_size + 20)
        fit = min(canvas_width / width, canvas_height / height)
        self.image_scale = max(required, fit)
        self.offset_x = self.winfo_width() / 2
        self.offset_y = self.winfo_height() / 2
        self._clamp_offset()

    def _scaled_size(self) -> tuple[int, int]:
        if self.source_image is None:
            return 1, 1
        return (
            max(1, round(self.source_image.width * self.image_scale)),
            max(1, round(self.source_image.height * self.image_scale)),
        )

    def _crop_box(self) -> tuple[float, float, float, float]:
        center_x = self.winfo_width() / 2
        center_y = self.winfo_height() / 2
        half = self.crop_size / 2
        return center_x - half, center_y - half, center_x + half, center_y + half

    def _clamp_offset(self) -> None:
        if self.source_image is None:
            return

        scaled_width, scaled_height = self._scaled_size()
        half_crop = self.crop_size / 2
        canvas_width = self.winfo_width()
        canvas_height = self.winfo_height()
        center_x = canvas_width / 2
        center_y = canvas_height / 2

        min_x = center_x + half_crop - scaled_width / 2
        max_x = center_x - half_crop + scaled_width / 2
        min_y = center_y + half_crop - scaled_height / 2
        max_y = center_y - half_crop + scaled_height / 2

        self.offset_x = min(max(self.offset_x, min_x), max_x)
        self.offset_y = min(max(self.offset_y, min_y), max_y)

    def _zoom(self, direction: int, mouse_x: float, mouse_y: float) -> None:
        if self.source_image is None:
            return

        old_scale = self.image_scale
        factor = ZOOM_FACTOR if direction > 0 else 1 / ZOOM_FACTOR
        new_scale = max(ZOOM_MIN, min(old_scale * factor, ZOOM_MAX))

        relative_x = (mouse_x - self.offset_x) / old_scale
        relative_y = (mouse_y - self.offset_y) / old_scale
        self.image_scale = new_scale
        self.offset_x = mouse_x - relative_x * new_scale
        self.offset_y = mouse_y - relative_y * new_scale
        self._clamp_offset()
        self.redraw()
        self._notify_change()
        self.on_status(f"Zoom {self.image_scale:.2f}×  •  Drag to reposition")

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        self._zoom(1 if event.delta > 0 else -1, event.x, event.y)

    def _on_mouse_down(self, event: tk.Event) -> None:
        if self.source_image is None:
            return
        self.dragging = True
        self.last_mouse = (event.x, event.y)
        self.configure(cursor="fleur")

    def _on_mouse_drag(self, event: tk.Event) -> None:
        if not self.dragging or self.source_image is None:
            return
        last_x, last_y = self.last_mouse
        self.offset_x += event.x - last_x
        self.offset_y += event.y - last_y
        self.last_mouse = (event.x, event.y)
        self._clamp_offset()
        self.redraw()
        self._notify_change()

    def _on_mouse_up(self, _event: tk.Event) -> None:
        self.dragging = False
        self.configure(cursor="crosshair")

    def get_cropped_image(self) -> Image.Image:
        if self.source_image is None:
            raise RuntimeError("No image imported.")

        x1, y1, x2, _y2 = self._crop_box()
        crop_width = x2 - x1

        source_x = (
            x1 - self.offset_x + (self.source_image.width * self.image_scale) / 2
        ) / self.image_scale
        source_y = (
            y1 - self.offset_y + (self.source_image.height * self.image_scale) / 2
        ) / self.image_scale
        source_crop = crop_width / self.image_scale

        max_x = max(0.0, self.source_image.width - source_crop)
        max_y = max(0.0, self.source_image.height - source_crop)
        source_x = max(0.0, min(source_x, max_x))
        source_y = max(0.0, min(source_y, max_y))

        return self.source_image.crop((source_x, source_y, source_x + source_crop, source_y + source_crop))

    def redraw(self) -> None:
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 2 or height < 2:
            return

        if self.source_image is None:
            self._draw_empty_state(width, height)
            return

        scaled_width, scaled_height = self._scaled_size()
        display = self.source_image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(display)
        self.create_image(self.offset_x, self.offset_y, image=self.preview_photo)

        x1, y1, x2, y2 = self._crop_box()

        # The four rectangles form a true crop overlay while keeping the image fully interactive.
        self.create_rectangle(0, 0, width, max(0, y1), fill="#000000", outline="")
        self.create_rectangle(0, y2, width, height, fill="#000000", outline="")
        self.create_rectangle(0, y1, x1, y2, fill="#000000", outline="")
        self.create_rectangle(x2, y1, width, y2, fill="#000000", outline="")

        border_color = THEME.white
        if self.round_variable.get():
            self.create_oval(x1, y1, x2, y2, outline=border_color, width=2)
            label = "ROUND CROP"
        else:
            self.create_rectangle(x1, y1, x2, y2, outline=border_color, width=2)
            label = "SQUARE CROP"

        third = self.crop_size / 3
        guide = {"fill": THEME.white, "width": 1, "dash": (4, 6)}
        for index in (1, 2):
            x = x1 + third * index
            y = y1 + third * index
            self.create_line(x, y1, x, y2, **guide)
            self.create_line(x1, y, x2, y, **guide)

        self.create_text(
            x1 + 10,
            y1 - 10,
            text=label,
            anchor="w",
            fill=THEME.white,
            font=("Segoe UI", 8, "bold"),
        )

    def _draw_empty_state(self, width: int, height: int) -> None:
        margin = 54
        x1, y1, x2, y2 = margin, margin, width - margin, height - margin
        self.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline=THEME.panel_border_light,
            width=2,
            dash=(7, 7),
        )

        center_x = width / 2
        center_y = height / 2
        self.create_line(center_x, center_y - 54, center_x, center_y - 83, fill=THEME.muted, width=3, capstyle="round")
        self.create_line(center_x, center_y - 83, center_x - 10, center_y - 72, fill=THEME.muted, width=3, capstyle="round")
        self.create_line(center_x, center_y - 83, center_x + 10, center_y - 72, fill=THEME.muted, width=3, capstyle="round")
        self.create_text(center_x, center_y - 30, text="Drop Image Here", fill=THEME.text, font=("Segoe UI", 13, "bold"))
        self.create_text(center_x, center_y - 2, text="or", fill=THEME.muted, font=("Segoe UI", 9))
        self.create_text(center_x, center_y + 25, text="Click to Import", fill=THEME.text, font=("Segoe UI", 12, "bold"))
        self.create_text(
            center_x,
            y2 + 22,
            text="Choose a square area, then drag and zoom to frame it",
            fill=THEME.muted,
            font=("Segoe UI", 9),
        )
