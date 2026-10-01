from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from PIL import Image, ImageDraw, ImageTk


class RoundedCard(tk.Frame):
    """Reusable sidebar card. Kept native Tkinter for zero extra UI dependencies."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        background: str,
        border: str,
        radius: int = 12,  # Kept in the API so the widget can later be upgraded visually without call-site changes.
        border_width: int = 1,
        padding: tuple[int, int] = (14, 14),
        **kwargs,
    ) -> None:
        del radius
        super().__init__(
            master,
            bg=background,
            bd=0,
            highlightthickness=border_width,
            highlightbackground=border,
            highlightcolor=border,
            **kwargs,
        )
        self.body = tk.Frame(self, bg=background, bd=0, highlightthickness=0)
        self.body.pack(fill="both", expand=True, padx=padding[0], pady=padding[1])


class FlatButton(tk.Button):
    def __init__(
        self,
        master: tk.Misc,
        *,
        text: str,
        command: Callable[[], None],
        background: str,
        hover: str,
        pressed: str,
        foreground: str,
        disabled: str,
        font: tuple[str, int, str] = ("Segoe UI", 9, "bold"),
        padx: int = 12,
        pady: int = 9,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            text=text,
            command=command,
            bg=background,
            fg=foreground,
            activebackground=hover,
            activeforeground=foreground,
            disabledforeground=disabled,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=font,
            cursor="hand2",
            padx=padx,
            pady=pady,
            **kwargs,
        )
        self._normal = background
        self._hover = hover
        self._pressed = pressed

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, _event: tk.Event) -> None:
        if str(self["state"]) != "disabled":
            self.configure(bg=self._hover)

    def _on_leave(self, _event: tk.Event) -> None:
        self.configure(bg=self._normal)

    def _on_press(self, _event: tk.Event) -> None:
        if str(self["state"]) != "disabled":
            self.configure(bg=self._pressed)

    def _on_release(self, _event: tk.Event) -> None:
        if str(self["state"]) != "disabled":
            self.configure(bg=self._hover)


class Switch(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        *,
        variable: tk.BooleanVar,
        on_change: Callable[[], None],
        on_color: str,
        off_color: str,
        knob_color: str,
        width: int = 40,
        height: int = 22,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            bg=master.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.variable = variable
        self.on_change = on_change
        self.on_color = on_color
        self.off_color = off_color
        self.knob_color = knob_color
        self._width = width
        self._height = height
        self.bind("<Button-1>", self._toggle)
        self.variable.trace_add("write", self._redraw)
        self._redraw()

    def _toggle(self, _event: tk.Event | None = None) -> None:
        self.variable.set(not self.variable.get())
        self.on_change()

    def _redraw(self, *_args) -> None:
        self.delete("all")
        r = self._height / 2
        fill = self.on_color if self.variable.get() else self.off_color
        self.create_oval(0, 0, self._height, self._height, fill=fill, outline=fill)
        self.create_rectangle(r, 0, self._width - r, self._height, fill=fill, outline=fill)
        self.create_oval(self._width - self._height, 0, self._width, self._height, fill=fill, outline=fill)

        knob_margin = 4
        knob = self._height - 2 * knob_margin
        if self.variable.get():
            left = self._width - knob - knob_margin
        else:
            left = knob_margin
        top = knob_margin
        self.create_oval(left, top, left + knob, top + knob, fill=self.knob_color, outline=self.knob_color)


class ProfilePreview(tk.Frame):
    """Small live preview used by the styling card."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        theme_bg: str,
        border: str,
        selected_border: str,
        round_mode: bool,
    ) -> None:
        super().__init__(
            master,
            bg=theme_bg,
            width=75,
            height=75,
            highlightbackground=border,
            highlightthickness=1,
        )
        self.pack_propagate(False)
        self._theme_bg = theme_bg
        self._border = border
        self._selected_border = selected_border
        self.round_mode = round_mode
        self._image: Image.Image | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self.canvas = tk.Canvas(self, width=75, height=75, bg=theme_bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.redraw()

    def set_image(self, image: Image.Image | None) -> None:
        self._image = image.copy().convert("RGBA") if image is not None else None
        self.redraw()

    def set_selected(self, selected: bool) -> None:
        self.configure(highlightbackground=self._selected_border if selected else self._border)

    def redraw(self) -> None:
        self.canvas.delete("all")
        center = 37
        radius = 29

        if self._image is not None:
            preview = self._image.resize((58, 58), Image.Resampling.LANCZOS).convert("RGBA")
            if self.round_mode:
                mask = Image.new("L", preview.size, 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 57, 57), fill=255)
                preview.putalpha(mask)
            self._photo = ImageTk.PhotoImage(preview)
            self.canvas.create_image(center, center, image=self._photo)
            outline = self._selected_border if self.round_mode else self._border
            if self.round_mode:
                self.canvas.create_oval(center - radius, center - radius, center + radius, center + radius, outline=outline, width=2)
            else:
                self.canvas.create_rectangle(center - radius, center - radius, center + radius, center + radius, outline=outline, width=2)
            return

        if self.round_mode:
            self.canvas.create_oval(center - radius, center - radius, center + radius, center + radius, fill="#4a4d54", outline=self._selected_border, width=2)
        else:
            self.canvas.create_rectangle(center - radius, center - radius, center + radius, center + radius, fill="#4a4d54", outline=self._border, width=2)
        self.canvas.create_oval(center - 10, center - 15, center + 10, center + 5, fill="#8f949f", outline="")
        self.canvas.create_arc(center - 22, center - 4, center + 22, center + 30, start=180, extent=180, fill="#8f949f", outline="#8f949f")


class ImageDropZone(tk.Frame):
    """Clickable image-import surface styled like a drag-and-drop target."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        background: str,
        border: str,
        foreground: str,
        muted: str,
        command: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=background, bd=0, highlightthickness=0, cursor="hand2")
        self._background = background
        self._border = border
        self._foreground = foreground
        self._muted = muted
        self._command = command

        self.canvas = tk.Canvas(self, bg=background, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", lambda _event: self._command())
        self.canvas.bind("<Enter>", self._hover)
        self.canvas.bind("<Leave>", self._leave)
        self.bind("<Configure>", self._draw)
        self._hovered = False

    def _hover(self, _event: tk.Event | None = None) -> None:
        self._hovered = True
        self._draw()

    def _leave(self, _event: tk.Event | None = None) -> None:
        self._hovered = False
        self._draw()

    def _draw(self, _event: tk.Event | None = None) -> None:
        self.update_idletasks()
        width = max(self.winfo_width(), 2)
        height = max(self.winfo_height(), 2)
        self.canvas.delete("all")

        stroke = "#666b77" if self._hovered else self._border
        x1, y1, x2, y2 = 12, 12, width - 12, height - 12
        self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline=stroke,
            width=2,
            dash=(7, 7),
        )

        cx = width / 2
        cy = height / 2 - 28
        # Upload arrow icon.
        self.canvas.create_line(cx, cy + 23, cx, cy - 8, fill=self.muted, width=3, capstyle="round")
        self.canvas.create_line(cx, cy - 8, cx - 11, cy + 4, fill=self.muted, width=3, capstyle="round")
        self.canvas.create_line(cx, cy - 8, cx + 11, cy + 4, fill=self.muted, width=3, capstyle="round")
        self.canvas.create_arc(cx - 23, cy + 11, cx + 23, cy + 35, start=180, extent=180, style="arc", outline=self.muted, width=3)

        self.canvas.create_text(cx, cy + 58, text="Drop Image Here", fill=self._foreground, font=("Segoe UI", 12, "bold"))
        self.canvas.create_text(cx, cy + 82, text="or", fill=self._muted, font=("Segoe UI", 9))
        self.canvas.create_text(cx, cy + 105, text="Click to Import", fill=self._foreground, font=("Segoe UI", 11, "bold"))

    @property
    def muted(self) -> str:
        return self._muted
