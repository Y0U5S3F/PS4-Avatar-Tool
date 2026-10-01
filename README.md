# HEN Avatar Maker

A maintainable desktop GUI for creating PS4 HEN avatar files from ordinary images.

## Why this implementation

The first version used Tkinter/Canvas heavily. That made exact widget sizing and platform rendering harder to control, which is what caused the overlapping switch label and cramped profile selectors seen in the screenshot.

This revision keeps the runtime dependency set small, but treats the UI as a set of dedicated components rather than one large widget. The import target is an independent widget, the crop editor owns crop state, and image/export code stays outside the UI layer.

For a larger production application, **PySide6 (Qt for Python)** would be my preferred UI toolkit because it gives you a stronger layout engine, high-DPI rendering, native desktop controls, accessibility support, and a much cleaner path to more complex views. I did not switch this build to an uninstalled dependency and pretend it was tested; this build is the one verified in the available runtime.

## Architecture

```text
HEN_avatar_maker_gui.py      compatibility launcher
main.py                      application entry point
hen_avatar_maker/
├── app.py                   UI composition + user actions
├── widgets.py               reusable controls
├── crop_view.py             pan / zoom / crop interaction
├── image_ops.py             image loading + output preparation
├── dxt5.py                  pure-Python DDS/DXT5 encoder
└── config.py                theme + application constants
tests/
└── test_core.py             core image/export tests
```

## Run

```bash
python -m pip install -r requirements.txt
python HEN_avatar_maker_gui.py
```

## Test

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

The verified build passes 4 automated tests plus a GUI smoke capture and an export smoke check.
