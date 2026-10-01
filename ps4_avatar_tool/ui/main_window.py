from __future__ import annotations

from pathlib import Path

from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    APP_SUBTITLE,
    APP_TITLE,
    SIDEBAR_WIDTH,
    SUPPORTED_IMAGE_FILTER,
    THEME,
    WINDOW_MIN_SIZE,
    WINDOW_SIZE,
)
from ..image_ops import ImageLoadError, export_avatar, load_image, validate_avatar_name
from .crop_editor import CropEditor
from .styles import build_stylesheet
from .widgets import Card, IconButton, ImportDropZone, ToggleSwitch


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*WINDOW_MIN_SIZE)
        self.setAcceptDrops(True)

        self.export_dir: Path | None = None
        self.round_profile = False

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
        self.crop_container.setObjectName("CropContainer")
        self.crop_container.setStyleSheet(
            f"QFrame#CropContainer {{ background: {THEME.canvas_bg}; border: 1px solid {THEME.border}; border-radius: 6px; }}"
        )
        crop_layout = QVBoxLayout(self.crop_container)
        crop_layout.setContentsMargins(1, 1, 1, 1)
        self.crop_editor = CropEditor()
        crop_layout.addWidget(self.crop_editor)
        self.crop_editor.fileDropped.connect(self.load_image_path)
        self.crop_editor.resized.connect(self._sync_drop_zone)
        self.crop_editor.zoomChanged.connect(self._on_zoom_changed)
        self.drop_zone = ImportDropZone(self.crop_editor)
        self.drop_zone.clicked.connect(self.import_image)
        self.drop_zone.fileDropped.connect(self.load_image_path)
        self.zoom_bar = self._build_zoom_bar()
        self._update_tool_buttons()
        self._sync_drop_zone()
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

        self.avatar_input = QLineEdit("CoolAvatar01")
        self.avatar_input.setPlaceholderText("e.g. CoolAvatar01")
        self.avatar_input.setClearButtonEnabled(True)
        layout.addWidget(self.avatar_input)

        label = QLabel("Export location")
        label.setStyleSheet(f"margin-top: 13px; color: {THEME.text}; font-size: 9pt;")
        layout.addWidget(label)

        location_row = QHBoxLayout()
        location_row.setContentsMargins(0, 7, 0, 0)
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
        row.setContentsMargins(0, 13, 0, 0)
        row.setSpacing(9)
        self.toggle = ToggleSwitch(False)
        self.toggle.toggled.connect(self._set_round_profile)
        row.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        toggle_label = QLabel("Apply Round Profile Crop")
        toggle_label.setStyleSheet(f"color: {THEME.text}; font-size: 9pt;")
        row.addWidget(toggle_label, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        layout.addLayout(row)

        return card

    def _build_zoom_bar(self) -> QFrame:
        """Small floating bar, bottom-right of the image area: rotate | - | zoom % | +"""
        bar = QFrame(self.crop_editor)
        bar.setObjectName("ZoomBar")
        bar.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
        bar.setStyleSheet(
            f"""
            QFrame#ZoomBar {{ background: rgba(16, 18, 22, 215); border: 1px solid {THEME.border}; border-radius: 6px; }}
            QFrame#ZoomBar QPushButton {{
                background: {THEME.panel_alt}; color: {THEME.text}; border: 0; border-radius: 4px;
                padding: 0; font-size: 13pt; font-weight: 600;
            }}
            QFrame#ZoomBar QPushButton:hover {{ background: {THEME.border_light}; }}
            QFrame#ZoomBar QPushButton:pressed {{ background: {THEME.border}; }}
            QFrame#ZoomBar QPushButton:disabled {{ background: #24262c; color: #5b606b; }}
            QFrame#ZoomBar QLabel {{ color: {THEME.text}; font-size: 9pt; font-weight: 600; background: transparent; }}
            """
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        def square_button(text: str, tooltip: str) -> QPushButton:
            button = QPushButton(text)
            button.setFixedSize(30, 30)
            button.setToolTip(tooltip)
            button.setAccessibleName(tooltip)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            return button

        self.rotate_button = square_button("\u21bb", "Rotate 90\u00b0 clockwise")
        self.rotate_button.clicked.connect(self._rotate_image)
        self.zoom_out_button = square_button("\u2212", "Zoom out")
        self.zoom_out_button.clicked.connect(self.crop_editor.zoom_out)
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_in_button = square_button("+", "Zoom in")
        self.zoom_in_button.clicked.connect(self.crop_editor.zoom_in)

        layout.addWidget(self.rotate_button)
        layout.addWidget(self.zoom_out_button)
        layout.addWidget(self.zoom_label)
        layout.addWidget(self.zoom_in_button)
        bar.adjustSize()
        bar.hide()
        return bar

    def _export_card(self) -> Card:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(9, 9, 9, 9)
        self.export_button = QPushButton("Create && Export Avatar")
        self.export_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_button.setMinimumHeight(54)
        self.export_button.setEnabled(False)
        self.export_button.setAccessibleName("Create and export avatar")
        self.export_button.setStyleSheet(
            f"""
            QPushButton {{ background: {THEME.blue}; color: {THEME.white}; border: 0; border-radius: 5px; font-size: 10pt; font-weight: 700; }}
            QPushButton:hover {{ background: {THEME.blue_hover}; }}
            QPushButton:pressed {{ background: {THEME.blue_pressed}; }}
            QPushButton:disabled {{ background: #2a2d33; color: #666b75; }}
            """
        )
        self.export_button.clicked.connect(self.export_current_avatar)
        layout.addWidget(self.export_button)
        return card

    def _sync_drop_zone(self) -> None:
        self._place_zoom_bar()
        if self.crop_editor.has_image:
            self.drop_zone.hide()
            return

        self.drop_zone.show()
        available = max(320, min(400, self.crop_editor.width() - 140))
        self.drop_zone.setFixedWidth(available)
        self.drop_zone.setFixedHeight(182)
        x = max(0, (self.crop_editor.width() - self.drop_zone.width()) // 2)
        y = max(0, (self.crop_editor.height() - self.drop_zone.height()) // 2 - 6)
        self.drop_zone.move(x, y)

    def _place_zoom_bar(self) -> None:
        has_image = self.crop_editor.has_image
        self.zoom_bar.setVisible(has_image)
        if not has_image:
            return
        margin = 12
        self.zoom_bar.adjustSize()
        self.zoom_bar.move(
            max(0, self.crop_editor.width() - self.zoom_bar.width() - margin),
            max(0, self.crop_editor.height() - self.zoom_bar.height() - margin),
        )
        self.zoom_bar.raise_()
        self._update_tool_buttons()

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

        self.crop_editor.set_image(image)
        self._sync_drop_zone()
        self.export_button.setEnabled(True)
        self._set_status(f"Loaded {Path(path).name}  •  {image.width}×{image.height}")

    def choose_export_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose export location")
        if path:
            self.export_dir = Path(path)
            self.location_input.setText(str(self.export_dir))
            self._set_status(f"Export location set to {self.export_dir}")

    def _set_round_profile(self, enabled: bool) -> None:
        self.round_profile = bool(enabled)
        self.crop_editor.set_round(self.round_profile)
        self._set_status(("Round" if enabled else "Square") + " profile picture mode selected")

    def _on_zoom_changed(self, scale: float) -> None:
        self._update_tool_buttons()
        self._set_status(f"Zoom {self._zoom_percent():.0f}%  •  Drag to reposition")

    def _rotate_image(self) -> None:
        self.crop_editor.rotate_clockwise()
        self._set_status("Rotated 90° clockwise  •  Drag to reposition")

    def _zoom_percent(self) -> float:
        editor = self.crop_editor
        return editor.scale / editor.min_scale() * 100.0 if editor.has_image else 100.0

    def _update_tool_buttons(self) -> None:
        editor = self.crop_editor
        self.zoom_label.setText(f"{self._zoom_percent():.0f}%")
        self.zoom_in_button.setEnabled(editor.can_zoom_in())
        self.zoom_out_button.setEnabled(editor.can_zoom_out())
        self.rotate_button.setEnabled(editor.has_image)

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
