# HEN Avatar Maker — PyQt6

A polished Windows-oriented desktop UI for creating PS4 HEN avatar files from any supported image.

## UI stack

- **PyQt6 / Qt 6 Widgets** for the desktop UI and high-DPI rendering.
- **Pillow** for robust image decoding, EXIF orientation, output resizing, masking, and DDS generation.
- **Custom QPainter widgets** for the crop overlay, import drop zone, toggle, folder icon, and profile selectors.

## Why the rewrite

The previous version used Tkinter `Canvas` for both UI composition and image rendering. This version uses Qt layouts for sizing and a dedicated painted crop editor so controls do not overlap and image movement does not require rebuilding the entire UI hierarchy.

## Layout

```text
HEN_avatar_maker_gui.py
hen_avatar_maker/
├── app.py                # QApplication lifecycle
├── config.py             # constants/theme
├── dxt5.py               # pure-Python DDS/DXT5 encoder
├── image_ops.py          # image loading + export
├── qt_image.py           # Pillow -> QImage ownership conversion
└── ui/
    ├── crop_editor.py    # pan/zoom/crop viewport
    ├── main_window.py    # screen composition + commands
    ├── styles.py         # central QSS
    └── widgets.py        # reusable controls
```

## Run

```bash
python -m pip install -r requirements.txt
python HEN_avatar_maker_gui.py
```

Drag-and-drop of a local image is supported in the import area. The crop editor supports mouse dragging and wheel zoom.

## Quality notes

- Qt's high-DPI scaling policy is enabled with `PassThrough`.
- The crop editor caches the scaled source for the current zoom level, so dragging only repaints the scene.
- The source image is never mutated during preview rendering.
- Pillow remains isolated from the UI layer except where a cropped image is passed to the export service.
