# OCR Hotkey

Copy text from your screen using local OCR on Windows. Press **Ctrl + Alt + Shift + O**, drag a rectangle around text, then paste the result with **Ctrl + V**.

Use it with text in images, videos, PDFs, remote desktops, and other screen content that you cannot select normally. Recognition quality depends on the text and image quality.

## Features

- Local PaddleOCR recognition with the PP-OCRv6 medium detection and recognition models.
- Native Windows global hotkey registration, without a keyboard-hook dependency.
- Selection overlays for multiple monitors, including displays with negative coordinates.
- Clipboard output, short status messages, and sound feedback.
- Background launch at sign-in, without a console window.
- Model preloading so subsequent captures reuse the loaded model.

## Requirements

- Windows with a desktop session.
- Python **3.11 or 3.12**, including Tkinter (included in the standard python.org Windows installer).
- Internet access to install dependencies and download the model weights on first use.
- Disk space for a PyTorch environment and the downloaded models. Setup downloads substantial dependencies; this repository does not bundle them.

The dependency versions in `requirements.txt` match the working Python 3.12 installation used for this project. Other operating systems and Python versions have not been validated.

## Install

Download this repository, or clone it:

```powershell
git clone https://github.com/Dolcruz/ocr-hotkey.git
cd ocr-hotkey
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-OcrHotkey.ps1
```

Setup creates `.venv` in the repository directory, installs dependencies, adds an **OCR Hotkey** shortcut to your Windows Startup folder, and starts the app. Keep the folder in its final location before running setup: the shortcut points to it.

Models download when the app first loads them. Let that finish before expecting the first capture to complete. Later runs reuse the model cache.

To start manually after installation, double-click `Start-OcrHotkey.cmd`.

## Use

1. Press **Ctrl + Alt + Shift + O**.
2. Drag over the text you want to copy and release the mouse.
3. Wait for the copied-text notification.
4. Paste with **Ctrl + V**.

Press **Esc** or right-click to cancel a selection. Each selected monitor region must be at least **6 x 6 pixels**. A selection spanning monitors is recognized per monitor and combined from left to right, then top to bottom. It is not stitched into a single image.

The app handles one OCR operation at a time. Further requests during recognition show a busy message. There is no application-level inference timeout; a slow or stalled inference keeps that operation occupied until it finishes or the process is stopped. If no text is found or recognition fails, the existing clipboard content is preserved.

## Command-line options

Run these after setup, from the repository folder:

```powershell
# Load the model on first capture instead of at startup.
.\.venv\Scripts\pythonw.exe .\ocr_hotkey.py --no-preload

# Choose a different hotkey for this launch.
.\.venv\Scripts\pythonw.exe .\ocr_hotkey.py --hotkey "<ctrl>+<shift>+f9"

# Recognize an image and print the text without starting the background app.
.\.venv\Scripts\python.exe .\ocr_hotkey.py --ocr-image .\example.png
```

Hotkeys accept `ctrl`/`control`, `alt`, `shift`, `win`/`windows`, ASCII letters and digits, F1-F24, and common navigation keys such as `space`, `escape`, `home`, and `page_down`. Windows or another app may already reserve a combination. Stop an existing instance before launching with a different hotkey. To keep a custom hotkey across sign-ins, add the same arguments to the Startup shortcut's target.

Image mode exits with code `0` when text is found and `2` when no text is found. It prints text to the terminal and does not copy it to the clipboard.

## Privacy and local files

Screen capture and OCR happen locally. The application does not send captures to an OCR service. Package installation and model downloads require network access; dependencies may contact their model sources during initialization.

**Selected screen regions are saved in the application folder** as `last_capture.png` and, for additional monitors, `last_capture_2.png`, etc. These files may contain sensitive information. Files from a previous multi-monitor capture can remain even after a later single-monitor capture. Delete them when you no longer need them. They are excluded from Git, along with logs and the virtual environment.

Recognized text is copied to the Windows clipboard. Windows clipboard history, clipboard synchronization, and other apps with clipboard access can retain or read it according to your system settings.

`ocr-hotkey.log` records application events, errors, capture geometry, and the number of recognized characters. The application does not intentionally log recognized text. Library exceptions can contain diagnostic details. Logs rotate at **1,000,000 bytes**, retaining **3 backups** plus the current log.

## Troubleshooting

- **Nothing happens on the hotkey:** check `ocr-hotkey.log`. A conflicting hotkey can prevent registration. The listener waits up to **5 seconds** for registration and checks its health every **5 seconds**, attempting to restart when stopped. These waits do not limit OCR inference.
- **First capture takes a while:** the models may still be downloading or loading. Run with `python.exe` in a terminal to see dependency output.
- **Setup fails:** use Python 3.11 or 3.12 and check the installation error. Setup stops after a failed environment, dependency, or shortcut command.
- **Need to stop the app:** open Task Manager, identify the Python process by the command line ending in this folder's `ocr_hotkey.py`, and end that process. The app currently has no tray menu or quit button. Avoid ending unrelated Python applications.

Listener shutdown waits up to **2 seconds** for its thread. If it has not stopped, the daemon thread may remain until the process exits.

## Remove automatic startup

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Remove-Startup.ps1
```

This removes the Startup shortcut. It does not stop an already running instance, remove the environment, delete captures, or delete cached model weights.

## Development

The regression tests use Python's standard library on Windows and do not load OCR models, register a global hotkey, or access your clipboard:

```powershell
python -m unittest discover -s tests -v
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test_setup.ps1
```

## Models and license

Recognition uses PaddleOCR's Transformers engine with the [PP-OCRv6 medium detector](https://huggingface.co/PaddlePaddle/PP-OCRv6_medium_det_safetensors) and [PP-OCRv6 medium recognizer](https://huggingface.co/PaddlePaddle/PP-OCRv6_medium_rec_safetensors).

The application code is licensed under the [MIT License](LICENSE). Dependencies and model weights retain their respective licenses; review their upstream terms when redistributing them.
