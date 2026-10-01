# HEN Avatar Maker — PyQt6

A maintainable PyQt6 rewrite of the HEN Avatar Maker desktop UI.

## Requirements

- Python 3.10+
- PyQt6 6.7+
- Pillow 10+

Install dependencies:

```text
python -m pip install -r requirements.txt
```

Start the application:

```text
python HEN_avatar_maker_gui.py
```

On Windows, the launcher also catches startup errors and displays a message box instead of silently closing. Runtime exceptions are logged to:

```text
%USERPROFILE%\HEN Avatar Maker\logs\application.log
```

## Architecture

```text
HEN_avatar_maker_gui.py      Safe desktop entry point
hen_avatar_maker/
├── app.py                   QApplication lifecycle + fatal-error handling
├── config.py                Theme and application constants
├── dxt5.py                  DDS/DXT5 encoder
├── image_ops.py             Pillow loading, masks, and export
├── qt_image.py              Pillow → Qt image conversion
└── ui/
    ├── crop_editor.py       Image pan/zoom/crop renderer
    ├── main_window.py       Window composition and application state
    ├── styles.py            Global Qt stylesheet
    └── widgets.py           Reusable custom widgets
```

The crop editor renders the source QPixmap through a `QPainter` transform rather than repeatedly creating resized raster copies while dragging. Vector overlays and controls use explicit `QColor` objects so Qt painting APIs receive the correct types.

## Validation

Run the core tests with:

```text
python -m pytest
```

The repository intentionally does not include generated caches or temporary smoke-test artifacts.
