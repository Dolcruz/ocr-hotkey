@echo off
set "APPDIR=%~dp0"
start "OCR Hotkey" "%APPDIR%.venv\Scripts\pythonw.exe" "%APPDIR%ocr_hotkey.py"
