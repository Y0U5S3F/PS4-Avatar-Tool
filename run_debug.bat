@echo off
setlocal
cd /d "%~dp0"
python HEN_avatar_maker_gui.py
if errorlevel 1 (
    echo.
    echo HEN Avatar Maker exited with an error.
    echo Check the log under %%USERPROFILE%%\HEN Avatar Maker\logs\application.log
    pause
)
endlocal
