$ErrorActionPreference = "Stop"

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "OCR Hotkey.lnk"
$pythonw = Join-Path $appDir ".venv\Scripts\pythonw.exe"
$script = Join-Path $appDir "ocr_hotkey.py"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = '"' + $script + '"'
$shortcut.WorkingDirectory = $appDir
$shortcut.Description = "Global OCR screen-region hotkey"
$shortcut.Save()

Write-Host "Installed startup shortcut: $shortcutPath"
