from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import (
    APP_SUBTITLE,
    APP_TITLE,
    SIDEBAR_WIDTH,
    SUPPORTED_IMAGE_TYPES,
    THEME,
    WINDOW_MIN_SIZE,
    WINDOW_SIZE,
)
from .crop_view import CropView
from .image_ops import ImageLoadError, export_avatar, load_image, validate_avatar_name
from .widgets import Card, FlatButton, ImageDropZone, ProfilePreview, Switch


class AvatarMakerApp(tk.Tk):
    """Application shell: UI composition, user actions, and state orchestration."""

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(*WINDOW_MIN_SIZE)
        self.configure(bg=THEME.bg)

        self.avatar_name = tk.StringVar(value="CoolAvatar01")
        self.export_dir = tk.StringVar(value="Choose a folder")
        self.is_round = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Ready to import an image.")
        self._preview_update_pending = False

        self._configure_style()
        self._build_ui()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TEntry", fieldbackground=THEME.panel_alt, background=THEME.panel_alt, foreground=THEME.text, insertcolor=THEME.text,
                        bordercolor=THEME.panel_border, lightcolor=THEME.panel_border, darkcolor=THEME.panel_border,
                        padding=(10, 7), font=("Segoe UI", 9))
        style.map("TEntry", bordercolor=[("focus", THEME.blue)], lightcolor=[("focus", THEME.blue)], darkcolor=[("focus", THEME.blue)])

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=THEME.bg)
        outer.pack(fill="both", expand=True, padx=22, pady=20)
        self._build_header(outer)

        content = tk.Frame(outer, bg=THEME.bg)
        content.pack(fill="both", expand=True, pady=(14, 0))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0, minsize=SIDEBAR_WIDTH)
        content.grid_rowconfigure(0, weight=1)

        self._build_crop_area(content)
        self._build_sidebar(content)

        footer = tk.Frame(outer, bg=THEME.bg)
        footer.pack(fill="x", pady=(10, 0))
        tk.Label(footer, textvariable=self.status, bg=THEME.bg, fg=THEME.muted,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x")

    def _build_header(self, parent: tk.Widget) -> None:
        header = tk.Frame(parent, bg=THEME.bg)
        header.pack(fill="x")
        tk.Label(header, text="HEN Avatar Maker", bg=THEME.bg, fg=THEME.text,
                 font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(header, text=APP_SUBTITLE, bg=THEME.bg, fg=THEME.muted,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

    def _build_crop_area(self, parent: tk.Widget) -> None:
        frame = tk.Frame(parent, bg=THEME.canvas_bg, highlightbackground=THEME.panel_border, highlightthickness=1)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        self.crop_view = CropView(frame, round_variable=self.is_round, on_status=self.status.set,
                                  on_change=self._schedule_preview_update)
        self.crop_view.pack(fill="both", expand=True, padx=1, pady=1)

        self.drop_zone = ImageDropZone(self.crop_view, background=THEME.canvas_bg, border=THEME.panel_border_light,
                                       foreground=THEME.text, muted=THEME.muted, command=self.import_image)
        self.crop_view.bind("<Configure>", self._sync_drop_zone, add="+")
        self.crop_view.after_idle(self._sync_drop_zone)

    def _sync_drop_zone(self, _event: tk.Event | None = None) -> None:
        if self.crop_view.source_image is not None:
            self.drop_zone.place_forget()
            return

        width = max(self.crop_view.winfo_width(), 1)
        height = max(self.crop_view.winfo_height(), 1)
        zone_width = max(330, min(385, width - 120))
        zone_height = 182
        if height < 360:
            zone_height = max(160, height // 3)
        self.drop_zone.place(relx=0.5, rely=0.49, anchor="center", width=zone_width, height=zone_height)

    def _build_sidebar(self, parent: tk.Widget) -> None:
        sidebar = tk.Frame(parent, bg=THEME.bg, width=SIDEBAR_WIDTH)
        sidebar.grid(row=0, column=1, sticky="ns")
        sidebar.grid_propagate(False)

        tk.Label(sidebar, text="CONTROLS", bg=THEME.bg, fg=THEME.text,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=2)
        tk.Label(sidebar, text="Crop, Shape, then Export.", bg=THEME.bg, fg=THEME.muted,
                 font=("Segoe UI", 8)).pack(anchor="w", padx=2, pady=(2, 14))

        self._build_project_card(sidebar)
        self._build_style_card(sidebar)
        self._build_export_button(sidebar)

    def _build_project_card(self, parent: tk.Widget) -> None:
        card = Card(parent, background=THEME.panel, border=THEME.panel_border, padding=(13, 13))
        card.pack(fill="x", pady=(0, 12))
        body = card.body
        tk.Label(body, text="Project Info", bg=THEME.panel, fg=THEME.text,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(body, text="Avatar name", bg=THEME.panel, fg=THEME.text,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(14, 6))
        ttk.Entry(body, textvariable=self.avatar_name).pack(fill="x")

        tk.Label(body, text="Export location", bg=THEME.panel, fg=THEME.text,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(13, 6))
        row = tk.Frame(body, bg=THEME.panel)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.export_dir, state="readonly").pack(side="left", fill="x", expand=True)
        FlatButton(row, text="⌕", command=self.choose_export_dir, background=THEME.panel_alt,
                   hover=THEME.panel_border_light, pressed=THEME.panel_border, foreground=THEME.text,
                   disabled="#666b76", font=("Segoe UI Symbol", 12), padx=8, pady=5).pack(side="left", padx=(6, 0))
        tk.Label(body, text="A folder with the avatar name will be created here.",
                 bg=THEME.panel, fg=THEME.muted, font=("Segoe UI", 8), justify="left", wraplength=238).pack(anchor="w", pady=(6, 0))

    def _build_style_card(self, parent: tk.Widget) -> None:
        card = Card(parent, background=THEME.panel, border=THEME.panel_border, padding=(13, 13))
        card.pack(fill="x", pady=(0, 12))
        body = card.body
        tk.Label(body, text="Avatar Styling", bg=THEME.panel, fg=THEME.text,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")

        switch_row = tk.Frame(body, bg=THEME.panel)
        switch_row.pack(fill="x", pady=(13, 12))
        Switch(switch_row, variable=self.is_round, on_change=self._on_shape_changed,
               on_color=THEME.blue, off_color=THEME.panel_border_light, knob_color=THEME.white).pack(side="left")
        tk.Label(switch_row, text="Apply Round Profile Crop", bg=THEME.panel, fg=THEME.text,
                 font=("Segoe UI", 9)).pack(side="left", padx=(9, 0))

        preview_row = tk.Frame(body, bg=THEME.panel)
        preview_row.pack(anchor="w")
        self.square_preview = ProfilePreview(preview_row, theme_bg=THEME.panel_alt, border=THEME.panel_border_light,
                                             selected_border=THEME.white, round_mode=False,
                                             command=lambda: self._select_shape(False))
        self.square_preview.pack(side="left")
        tk.Label(preview_row, text="or", bg=THEME.panel, fg=THEME.muted,
                 font=("Segoe UI", 8)).pack(side="left", padx=9)
        self.round_preview = ProfilePreview(preview_row, theme_bg=THEME.panel_alt, border=THEME.panel_border_light,
                                            selected_border=THEME.blue, round_mode=True,
                                            command=lambda: self._select_shape(True))
        self.round_preview.pack(side="left")
        self._update_previews()

    def _build_export_button(self, parent: tk.Widget) -> None:
        card = Card(parent, background=THEME.panel, border=THEME.panel_border, padding=(9, 9))
        card.pack(fill="x")
        FlatButton(card.body, text="Create & Export Avatar", command=self.export_current_avatar,
                   background=THEME.blue, hover=THEME.blue_hover, pressed=THEME.blue_pressed,
                   foreground=THEME.white, disabled="#b5bcc7", font=("Segoe UI", 10, "bold"),
                   pady=11).pack(fill="x")

    def _select_shape(self, round_mode: bool) -> None:
        if self.is_round.get() != round_mode:
            self.is_round.set(round_mode)
        else:
            self._on_shape_changed()

    def _schedule_preview_update(self) -> None:
        if self._preview_update_pending:
            return
        self._preview_update_pending = True
        self.after_idle(self._flush_preview_update)

    def _flush_preview_update(self) -> None:
        self._preview_update_pending = False
        self._update_previews()

    def _update_previews(self) -> None:
        if not hasattr(self, "crop_view"):
            return
        cropped = None
        if self.crop_view.source_image is not None:
            try:
                cropped = self.crop_view.get_cropped_image()
            except RuntimeError:
                pass
        self.square_preview.set_image(cropped)
        self.round_preview.set_image(cropped)
        self.square_preview.set_selected(not self.is_round.get())
        self.round_preview.set_selected(self.is_round.get())

    def _on_shape_changed(self) -> None:
        self.crop_view.set_round_mode()
        self._update_previews()
        mode = "Round" if self.is_round.get() else "Square"
        self.status.set(f"{mode} profile picture mode selected")

    def choose_export_dir(self) -> None:
        selected = filedialog.askdirectory(title="Choose export location")
        if selected:
            self.export_dir.set(selected)
            self.status.set(f"Export location set to {selected}")

    def import_image(self) -> None:
        path = filedialog.askopenfilename(title="Import image", filetypes=SUPPORTED_IMAGE_TYPES)
        if not path:
            return
        try:
            image = load_image(path)
        except ImageLoadError as exc:
            messagebox.showerror("Import failed", str(exc), parent=self)
            return

        self.crop_view.set_image(image)
        self._sync_drop_zone()
        self._update_previews()
        self.status.set(f"Loaded {Path(path).name}  •  {image.width}×{image.height}")

    def export_current_avatar(self) -> None:
        if self.crop_view.source_image is None:
            messagebox.showwarning("No image", "Import an image before exporting.", parent=self)
            return
        try:
            validate_avatar_name(self.avatar_name.get())
        except ValueError as exc:
            messagebox.showwarning("Invalid avatar name", str(exc), parent=self)
            return

        if self.export_dir.get() == "Choose a folder":
            self.choose_export_dir()
            if self.export_dir.get() == "Choose a folder":
                return

        try:
            output_dir = export_avatar(cropped=self.crop_view.get_cropped_image(), output_parent=self.export_dir.get(),
                                       avatar_name=self.avatar_name.get(), round_profile=self.is_round.get())
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Export failed", f"Could not create the avatar files.\n\n{exc}", parent=self)
            return

        shape = "round" if self.is_round.get() else "square"
        self.status.set(f"Exported {shape} avatar to {output_dir}")
        messagebox.showinfo("Export complete", f"Your {shape} avatar files are ready.\n\n{output_dir}", parent=self)


def main() -> None:
    AvatarMakerApp().mainloop()
