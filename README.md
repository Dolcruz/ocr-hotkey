# OCR Hotkey

Windows screen-region OCR with a global hotkey.

Press Ctrl+Alt+Shift+O, drag a box over text on any monitor, and the recognized text is copied to your clipboard.

## What It Uses

- PaddleOCR with PP-OCRv6_medium_det
- PaddleOCR with PP-OCRv6_medium_rec
- The Transformers engine and safetensors model weights
- A per-monitor capture overlay for multi-display Windows setups

The detector model finds text boxes; the recognition model turns those boxes into text. Both are needed for clipboard OCR.

## Install

Requirements:

- Windows
- Python 3.11 or 3.12
- Internet access on first setup so the Python packages and OCR model files can download

Run this in PowerShell from the repo folder:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-OcrHotkey.ps1

The setup script creates .venv, installs dependencies, adds a Startup shortcut, and starts the background hotkey app.

## Use

1. Press Ctrl+Alt+Shift+O.
2. Drag a box over the text you want.
3. Release the mouse.
4. Paste anywhere with Ctrl+V.

The first OCR run can take a moment while the model warms up.

## Files

- ocr_hotkey.py - background hotkey and OCR app
- Setup-OcrHotkey.ps1 - one-command setup
- Start-OcrHotkey.cmd - manual launcher
- Install-Startup.ps1 - installs the Startup shortcut
- Remove-Startup.ps1 - removes the Startup shortcut
- requirements.txt - pinned Python dependencies

Runtime files such as .venv, logs, and last captures are ignored by Git.

## Remove Startup Entry

    powershell -NoProfile -ExecutionPolicy Bypass -File .\Remove-Startup.ps1
