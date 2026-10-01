# PS4 Avatar Tool — PyQt6

PyQt6 desktop application for creating PS4 Avatar assets from an image.

## Important runtime fix in 1.0.0

The GUI uses explicit `QPainter.begin()` / `QPainter.end()` ownership with `try/finally` in every custom-painted widget. The Qt application also catches exceptions at the event-dispatch boundary and defers diagnostic dialogs until the current event has completed.

This avoids the common failure mode where an exception inside `paintEvent()` leaves the Qt backing store in an active-painter state and produces repeated messages such as:

```text
QBackingStore::endPaint() called with active painter; did you forget to destroy it or call QPainter::end() on it?
```

Custom painting has been reduced to the crop editor, toggle, and import drop zone. The folder button now uses Qt's native folder icon instead of a second custom paint path.

## Install

```text
python -m pip install -r requirements.txt
```

## Run

```text
python ps4_avatar_tool_gui.py
```

For debugging on Windows, use `run_debug.bat` so the console stays open after a failure.

## Tests

```text
python -m pytest
```

## Logs

```text
%USERPROFILE%\\PS4 Avatar Tool\\logs\\application.log
```
