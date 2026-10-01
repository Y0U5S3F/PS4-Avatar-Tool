# HEN Avatar Maker

A modular Tkinter/Pillow desktop app for creating PS4 HEN avatar assets from an image.

## UI

The layout follows the supplied reference: dark workspace, large crop editor on the left, and compact control cards on the right for project information, styling, and export.

## Project structure

```text
HEN_avatar_maker_gui.py    # compatibility launcher
main.py                     # normal entry point
requirements.txt
hen_avatar_maker/
  __init__.py
  app.py                    # window + UI composition + commands
  config.py                 # constants, theme, file filters
  crop_view.py              # pan/zoom crop editor
  dxt5.py                   # pure-Python DXT5 DDS encoder
  image_ops.py              # image loading, masking, validation, export
  widgets.py                # reusable UI widgets
```

## Run

```bash
python -m pip install -r requirements.txt
python HEN_avatar_maker_gui.py
```

The import surface is intentionally drawn as a drag-and-drop target to match the reference UI; clicking the target opens the native file picker. No third-party Tk drag-and-drop package is required.
