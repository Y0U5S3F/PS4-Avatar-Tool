from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from PIL import Image

from ..config import APP_SUBTITLE, APP_TITLE, SIDEBAR_WIDTH, SUPPORTED_IMAGE_FILTER, THEME, WINDOW_MIN_SIZE, WINDOW_SIZE
from ..image_ops import ImageLoadError, export_avatar, load_image, validate_avatar_name
from .crop_editor import CropEditor
from .styles import build_stylesheet
from .widgets import Card, IconButton, ImportDropZone, ProfilePreview, ToggleSwitch


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*WINDOW_MIN_SIZE)
        self.setAcceptDrops(True)

        self.avatar_name = "CoolAvatar01"
        self.export_dir: Path | None = None
        self.round_profile = False
        self._current_image: Image.Image | None = None
        self._preview_update_pending = False

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        root.setStyleSheet(build_stylesheet())
        self._build_ui(root)

    def _build_ui(self, root: QWidget) -> None:
        shell = QVBoxLayout(root)
        shell.setContentsMargins(22, 20, 22, 17)
        shell.setSpacing(0)

        shell.addWidget(self._header())
        shell.addSpacing(16)

        content = QHBoxLayout()
        content.setSpacing(14)
        shell.addLayout(content, 1)

        self.crop_container = QFrame()
        self.crop_container.setStyleSheet(
            f"QFrame {{ background: {THEME.canvas_bg}; border: 1px solid {THEME.border}; border-radius: 6px; }}"
        )
        crop_layout = QVBoxLayout(self.crop_container)
        crop_layout.setContentsMargins(1, 1, 1, 1)
        self.crop_editor = CropEditor()
        crop_layout.addWidget(self.crop_editor)
        self.crop_editor.fileDropped.connect(self.load_image_path)
        self.crop_editor.resized.connect(self._sync_drop_zone)
        self.drop_zone = ImportDropZone(self.crop_editor)
        self.drop_zone.clicked.connect(self.import_image)
        self.drop_zone.fileDropped.connect(self.load_image_path)
        self._sync_drop_zone()
        self.crop_editor.zoomChanged.connect(lambda scale: self._set_status(f"Zoom {scale:.2f}×  •  Drag to reposition"))
        self.crop_editor.changed.connect(self._schedule_preview_update)
        content.addWidget(self.crop_container, 1)

        sidebar = self._sidebar()
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        content.addWidget(sidebar)

        self.status = QLabel("Ready to import an image.")
        self.status.setStyleSheet(f"color: {THEME.muted}; font-size: 9pt;")
        self.status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        shell.addSpacing(10)
        shell.addWidget(self.status)

    def _header(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        title = QLabel(APP_TITLE)
        title.setStyleSheet(f"color: {THEME.text}; font-size: 23pt; font-weight: 700;")
        subtitle = QLabel(APP_SUBTITLE)
        subtitle.setStyleSheet(f"color: {THEME.muted}; font-size: 9pt;")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return widget

    def _sidebar(self) -> QWidget:
        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(12)

        controls = QLabel("CONTROLS")
        controls.setStyleSheet(f"color: {THEME.text}; font-size: 10pt; font-weight: 700;")
        hint = QLabel("Crop, Shape, then Export.")
        hint.setStyleSheet(f"color: {THEME.muted}; font-size: 8pt;")
        side_layout.addWidget(controls)
        side_layout.addWidget(hint)

        side_layout.addWidget(self._project_card())
        side_layout.addWidget(self._style_card())
        side_layout.addWidget(self._export_card())
        side_layout.addStretch(1)
        return side

    def _project_card(self) -> Card:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(13, 12, 13, 13)
        layout.setSpacing(0)

        title = QLabel("Project Info")
        title.setStyleSheet(f"font-size: 10pt; font-weight: 700; color: {THEME.text};")
        layout.addWidget(title)

        label = QLabel("Avatar name")
        label.setStyleSheet(f"margin-top: 14px; color: {THEME.text}; font-size: 9pt;")
        layout.addWidget(label)

        self.avatar_input = QLineEdit(self.avatar_name)
        self.avatar_input.setPlaceholderText("e.g. CoolAvatar01")
        layout.addWidget(self.avatar_input)

        label = QLabel("Export location")
        label.setStyleSheet(f"margin-top: 13px; color: {THEME.text}; font-size: 9pt;")
        layout.addWidget(label)

        location_row = QHBoxLayout()
        location_row.setSpacing(6)
        self.location_input = QLineEdit("Choose a folder")
        self.location_input.setReadOnly(True)
        location_row.addWidget(self.location_input, 1)
        self.folder_button = IconButton()
        self.folder_button.clicked.connect(self.choose_export_dir)
        location_row.addWidget(self.folder_button)
        layout.addLayout(location_row)

        helper = QLabel("A folder with the avatar name will be created here.")
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {THEME.muted}; font-size: 8pt; margin-top: 7px;")
        layout.addWidget(helper)
        return card

    def _style_card(self) -> Card:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(13, 12, 13, 13)
        layout.setSpacing(0)

        title = QLabel("Avatar Styling")
        title.setStyleSheet(f"font-size: 10pt; font-weight: 700; color: {THEME.text};")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setContentsMargins(0, 13, 0, 12)
        row.setSpacing(9)
        self.toggle = ToggleSwitch(False)
        self.toggle.toggled.connect(self._set_round_profile)
        row.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        toggle_label = QLabel("Apply Round Profile Crop")
        toggle_label.setStyleSheet(f"color: {THEME.text}; font-size: 9pt;")
        row.addWidget(toggle_label, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        layout.addLayout(row)

        previews = QHBoxLayout()
        previews.setSpacing(8)
        self.square_preview = ProfilePreview(False)
        self.square_preview.clicked.connect(self._select_shape)
        self.round_preview = ProfilePreview(True)
        self.round_preview.clicked.connect(self._select_shape)
        previews.addWidget(self.square_preview)
        or_label = QLabel("or")
        or_label.setStyleSheet(f"color: {THEME.muted}; font-size: 8pt;")
        previews.addWidget(or_label, 0, Qt.AlignmentFlag.AlignVCenter)
        previews.addWidget(self.round_preview)
        previews.addStretch(1)
        layout.addLayout(previews)
        self._update_preview_selection()
        return card

    def _export_card(self) -> Card:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(9, 9, 9, 9)
        from PyQt6.QtWidgets import QPushButton
        export_button = QPushButton("Create & Export Avatar")
        export_button.setCursor(Qt.CursorShape.PointingHandCursor)
        export_button.setMinimumHeight(54)
        export_button.setStyleSheet(
            f"""
            QPushButton {{ background: {THEME.blue}; color: {THEME.white}; border: 0; border-radius: 5px; font-size: 10pt; font-weight: 700; }}
            QPushButton:hover {{ background: {THEME.blue_hover}; }}
            QPushButton:pressed {{ background: {THEME.blue_pressed}; }}
            """
        )
        export_button.clicked.connect(self.export_current_avatar)
        layout.addWidget(export_button)
        return card

    def _sync_drop_zone(self) -> None:
        if self.crop_editor.has_image:
            self.drop_zone.hide()
            return
        self.drop_zone.show()
        width = min(max(self.crop_editor.width() - 120, 330), 385)
        self.drop_zone.setFixedWidth(width)
        self.drop_zone.setFixedHeight(182)
        self.drop_zone.adjustSize()
        x = (self.crop_editor.width() - self.drop_zone.width()) // 2
        y = max(0, (self.crop_editor.height() - self.drop_zone.height()) // 2 - 4)
        self.drop_zone.move(x, y)

    def import_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import image", "", SUPPORTED_IMAGE_FILTER)
        if path:
            self.load_image_path(path)

    def load_image_path(self, path: str) -> None:
        try:
            image = load_image(path)
        except ImageLoadError as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return

        self._current_image = image
        self.crop_editor.set_image(image)
        self._sync_drop_zone()
        self._set_status(f"Loaded {Path(path).name}  •  {image.width}×{image.height}")
        self._update_previews()

    def choose_export_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose export location")
        if path:
            self.export_dir = Path(path)
            self.location_input.setText(str(self.export_dir))
            self._set_status(f"Export location set to {self.export_dir}")

    def _select_shape(self, round_mode: bool) -> None:
        self.toggle.setChecked(round_mode)
        self._set_round_profile(round_mode)

    def _set_round_profile(self, enabled: bool) -> None:
        self.round_profile = bool(enabled)
        self.crop_editor.set_round(self.round_profile)
        self._update_preview_selection()
        self._set_status(("Round" if enabled else "Square") + " profile picture mode selected")

    def _update_preview_selection(self) -> None:
        self.square_preview.setSelected(not self.round_profile)
        self.round_preview.setSelected(self.round_profile)

    def _schedule_preview_update(self) -> None:
        if self._preview_update_pending:
            return
        self._preview_update_pending = True
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._flush_preview_update)

    def _flush_preview_update(self) -> None:
        self._preview_update_pending = False
        self._update_previews()

    def _update_previews(self) -> None:
        if not self.crop_editor.has_image:
            self.square_preview.setImage(None)
            self.round_preview.setImage(None)
            return
        try:
            crop = self.crop_editor.get_cropped_image()
        except RuntimeError:
            return
        self.square_preview.setImage(crop)
        self.round_preview.setImage(crop)
        self._update_preview_selection()

    def export_current_avatar(self) -> None:
        try:
            avatar_name = validate_avatar_name(self.avatar_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid avatar name", str(exc))
            return
        if not self.crop_editor.has_image:
            QMessageBox.warning(self, "No image", "Import an image before exporting.")
            return
        if self.export_dir is None:
            self.choose_export_dir()
            if self.export_dir is None:
                return

        try:
            output_dir = export_avatar(
                cropped=self.crop_editor.get_cropped_image(),
                output_parent=self.export_dir,
                avatar_name=avatar_name,
                round_profile=self.round_profile,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, "Export failed", f"Could not create the avatar files.\n\n{exc}")
            return

        self.location_input.setText(str(self.export_dir))
        shape = "round" if self.round_profile else "square"
        self._set_status(f"Exported {shape} avatar to {output_dir}")
        QMessageBox.information(self, "Export complete", f"Your {shape} avatar files are ready.\n\n{output_dir}")

    def _set_status(self, message: str) -> None:
        self.status.setText(message)
