@echo off
setlocal

python -m pip install --upgrade pillow pyinstaller
if errorlevel 1 (
    echo.
    echo Failed to install/build dependencies.
    pause
    exit /b 1
)

python -m PyInstaller --noconfirm --clean --onefile --windowed --name HEN_Avatar_Maker HEN_avatar_maker_gui.py
if errorlevel 1 (
    echo.
    echo PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo Build complete: dist\HEN_Avatar_Maker.exe
echo.
pause
