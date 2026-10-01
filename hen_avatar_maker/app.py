from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import (
    APP_SUBTITLE,
    APP_TITLE,
    OUTPUT_PREVIEW_NAMES,
    SIDEBAR_WIDTH,
    SUPPORTED_IMAGE_TYPES,
    THEME,
    WINDOW_MIN_SIZE,
    WINDOW_SIZE,
)
from .crop_view import CropView
from .image_ops import ImageLoadError, export_avatar, load_image, validate_avatar_name
from .widgets import FlatButton, ImageDropZone, ProfilePreview, RoundedCard, Switch


class AvatarMakerApp(tk.Tk):
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

        self._configure_window_style()
        self._build_ui()

    def _configure_window_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=THEME.bg)
        style.configure(
            "Title.TLabel",
            background=THEME.bg,
            foreground=THEME.text,
            font=("Segoe UI", 23, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=THEME.bg,
            foreground=THEME.muted,
            font=("Segoe UI", 9),
        )
        style.configure(
            "CardTitle.TLabel",
            background=THEME.panel,
            foreground=THEME.text,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "CardLabel.TLabel",
            background=THEME.panel,
            foreground=THEME.text,
            font=("Segoe UI", 9),
        )
        style.configure(
            "CardHint.TLabel",
            background=THEME.panel,
            foreground=THEME.muted,
            font=("Segoe UI", 8),
        )
        style.configure(
            "TEntry",
            fieldbackground=THEME.panel_alt,
            background=THEME.panel_alt,
            foreground=THEME.text,
            insertcolor=THEME.text,
            bordercolor=THEME.panel_border,
            lightcolor=THEME.panel_border,
            darkcolor=THEME.panel_border,
            padding=(10, 8),
            font=("Segoe UI", 9),
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", THEME.blue)],
            lightcolor=[("focus", THEME.blue)],
            darkcolor=[("focus", THEME.blue)],
        )

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
        tk.Label(
            footer,
            textvariable=self.status,
            bg=THEME.bg,
            fg=THEME.muted,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x")

    def _build_header(self, parent: tk.Widget) -> None:
        header = tk.Frame(parent, bg=THEME.bg)
        header.pack(fill="x")

        title_row = tk.Frame(header, bg=THEME.bg)
        title_row.pack(fill="x")
        tk.Label(
            title_row,
            text="🪶",
            bg=THEME.bg,
            fg=THEME.blue,
            font=("Segoe UI Emoji", 12),
        ).pack(side="left", padx=(0, 7))
        ttk.Label(title_row, text=APP_TITLE, style="Title.TLabel").pack(side="left")
        ttk.Label(header, text=APP_SUBTITLE, style="Subtitle.TLabel").pack(anchor="w", padx=(27, 0), pady=(0, 2))

    def _build_crop_area(self, parent: tk.Widget) -> None:
        frame = tk.Frame(
            parent,
            bg=THEME.canvas_bg,
            highlightbackground=THEME.panel_border,
            highlightthickness=1,
            bd=0,
        )
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        self.crop_view = CropView(
            frame,
            round_variable=self.is_round,
            on_status=self.status.set,
            on_change=self._schedule_preview_update,
        )
        self.crop_view.pack(fill="both", expand=True, padx=1, pady=1)
        self.drop_zone = ImageDropZone(
            self.crop_view,
            background=THEME.canvas_bg,
            border=THEME.panel_border_light,
            foreground=THEME.text,
            muted=THEME.muted,
            command=self.import_image,
        )
        # Drop zone is only visible before an image is loaded; it floats over the crop canvas.
        self._sync_drop_zone()
        self.crop_view.after_idle(self._sync_drop_zone)
        self.crop_view.bind("<Configure>", self._sync_drop_zone, add="+")

    def _sync_drop_zone(self, _event: tk.Event | None = None) -> None:
        visible = self.crop_view.source_image is None
        if visible:
            if not self.drop_zone.winfo_ismapped():
                self.drop_zone.place(relx=0.5, rely=0.5, relwidth=0.48, relheight=0.31, anchor="center")
        else:
            self.drop_zone.place_forget()

    def _build_sidebar(self, parent: tk.Widget) -> None:
        sidebar = tk.Frame(parent, bg=THEME.bg)
        sidebar.grid(row=0, column=1, sticky="ns")

        tk.Label(
            sidebar,
            text="CONTROLS",
            bg=THEME.bg,
            fg=THEME.text,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=2)
        tk.Label(
            sidebar,
            text="Crop, Shape, then Export.",
            bg=THEME.bg,
            fg=THEME.muted,
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=2, pady=(2, 14))

        self._build_project_card(sidebar)
        self._build_style_card(sidebar)
        self._build_export_button(sidebar)

    def _build_project_card(self, parent: tk.Widget) -> None:
        card = RoundedCard(
            parent,
            background=THEME.panel,
            border=THEME.panel_border,
            radius=11,
            padding=(14, 14),
            height=188,
        )
        card.pack(fill="x", pady=(0, 12))

        body = card.body
        ttk.Label(body, text="Project Info", style="CardTitle.TLabel").pack(anchor="w")

        ttk.Label(body, text="Avatar name", style="CardLabel.TLabel").pack(anchor="w", pady=(14, 6))
        ttk.Entry(body, textvariable=self.avatar_name).pack(fill="x")

        ttk.Label(body, text="Export location", style="CardLabel.TLabel").pack(anchor="w", pady=(13, 6))
        location_row = tk.Frame(body, bg=THEME.panel)
        location_row.pack(fill="x")
        location = ttk.Entry(location_row, textvariable=self.export_dir, state="readonly")
        location.pack(side="left", fill="x", expand=True)
        browse = FlatButton(
            location_row,
            text="📁",
            command=self.choose_export_dir,
            background=THEME.panel_alt,
            hover=THEME.panel_border_light,
            pressed=THEME.panel_border,
            foreground=THEME.text,
            disabled="#666b76",
            font=("Segoe UI Emoji", 10),
            padx=8,
            pady=7,
        )
        browse.pack(side="left", padx=(6, 0))

        ttk.Label(
            body,
            text="A folder with the avatar name will be created here.",
            style="CardHint.TLabel",
            wraplength=236,
        ).pack(anchor="w", pady=(6, 0))

    def _build_style_card(self, parent: tk.Widget) -> None:
        card = RoundedCard(
            parent,
            background=THEME.panel,
            border=THEME.panel_border,
            radius=11,
            padding=(14, 14),
            height=168,
        )
        card.pack(fill="x", pady=(0, 12))
        body = card.body

        ttk.Label(body, text="Avatar Styling", style="CardTitle.TLabel").pack(anchor="w")

        switch_row = tk.Frame(body, bg=THEME.panel)
        switch_row.pack(fill="x", pady=(13, 11))
        Switch(
            switch_row,
            variable=self.is_round,
            on_change=self._on_shape_changed,
            on_color=THEME.blue,
            off_color=THEME.panel_border_light,
            knob_color=THEME.white,
        ).pack(side="left")
        tk.Label(
            switch_row,
            text="Apply Round Profile Crop",
            bg=THEME.panel,
            fg=THEME.text,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(9, 0))

        preview_row = tk.Frame(body, bg=THEME.panel)
        preview_row.pack(fill="x")
        self.square_preview = ProfilePreview(
            preview_row,
            theme_bg=THEME.panel_alt,
            border=THEME.panel_border_light,
            selected_border=THEME.white,
            round_mode=False,
        )
        self.square_preview.pack(side="left")

        tk.Label(
            preview_row,
            text="or",
            bg=THEME.panel,
            fg=THEME.muted,
            font=("Segoe UI", 8),
        ).pack(side="left", padx=10)
        self.round_preview = ProfilePreview(
            preview_row,
            theme_bg=THEME.panel_alt,
            border=THEME.panel_border_light,
            selected_border=THEME.blue,
            round_mode=True,
        )
        self.round_preview.pack(side="left")
        self._update_previews()

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
        source = self.crop_view.source_image
        cropped = None
        if source is not None:
            try:
                cropped = self.crop_view.get_cropped_image()
            except RuntimeError:
                cropped = None
        self.square_preview.set_image(cropped)
        self.round_preview.set_image(cropped)
        self.square_preview.set_selected(not self.is_round.get())
        self.round_preview.set_selected(self.is_round.get())

    def _build_export_button(self, parent: tk.Widget) -> None:
        card = RoundedCard(
            parent,
            background=THEME.panel,
            border=THEME.panel_border,
            radius=11,
            padding=(0, 0),
            height=66,
        )
        card.pack(fill="x")

        button = FlatButton(
            card.body,
            text="Create & Export Avatar",
            command=self.export_current_avatar,
            background=THEME.blue,
            hover=THEME.blue_hover,
            pressed=THEME.blue_pressed,
            foreground=THEME.white,
            disabled="#b5bcc7",
            font=("Segoe UI", 10, "bold"),
            pady=11,
        )
        button.pack(fill="both", expand=True, padx=9, pady=9)

    def choose_export_dir(self) -> None:
        selected = filedialog.askdirectory(title="Choose export location")
        if not selected:
            return
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
        name = Path(path).name
        self.status.set(f"Loaded {name}  •  {image.width}×{image.height}")

    def _on_shape_changed(self) -> None:
        self.crop_view.set_round_mode()
        mode = "Round" if self.is_round.get() else "Square"
        self.status.set(f"{mode} profile picture mode selected")

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
            cropped = self.crop_view.get_cropped_image()
            output_dir = export_avatar(
                cropped=cropped,
                output_parent=self.export_dir.get(),
                avatar_name=self.avatar_name.get(),
                round_profile=self.is_round.get(),
            )
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Export failed", f"Could not create the avatar files.\n\n{exc}", parent=self)
            return

        shape = "round" if self.is_round.get() else "square"
        self.status.set(f"Exported {shape} avatar to {output_dir}")
        messagebox.showinfo(
            "Export complete",
            f"Your {shape} avatar files are ready.\n\n{output_dir}",
            parent=self,
        )


def main() -> None:
    app = AvatarMakerApp()
    app.mainloop()
