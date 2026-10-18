$ErrorActionPreference = "Stop"

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $appDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$requirements = Join-Path $appDir "requirements.txt"
$installStartup = Join-Path $appDir "Install-Startup.ps1"
$script = Join-Path $appDir "ocr_hotkey.py"

function Resolve-Python {
    $candidates = @(
        @{ Command = "py"; Args = @("-3.12") },
        @{ Command = "py"; Args = @("-3.11") },
        @{ Command = "python"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate.Command -ErrorAction SilentlyContinue
        if (-not $command) {
            continue
        }

        try {
            & $candidate.Command @($candidate.Args + @("-c", "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] <= (3, 12) else 1)"))
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
            continue
        }
    }

    throw "Python 3.11 or 3.12 was not found. Install Python from https://www.python.org/downloads/windows/ and re-run this script."
}

Set-Location $appDir
$python = Resolve-Python

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creating virtual environment..."
    & $python.Command @($python.Args + @("-m", "venv", $venvDir))
    if ($LASTEXITCODE -ne 0) { throw "Failed to create the virtual environment." }
}

Write-Host "Installing Python packages. This can take several minutes..."
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }
& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) { throw "Failed to install dependencies. Startup was not installed." }

Write-Host "Installing startup shortcut..."
& powershell -NoProfile -ExecutionPolicy Bypass -File $installStartup
if ($LASTEXITCODE -ne 0) { throw "Failed to install the startup shortcut." }

Write-Host "Starting OCR hotkey..."
$pythonw = Join-Path $venvDir "Scripts\pythonw.exe"
$argument = '"' + $script + '"'
Start-Process -FilePath $pythonw -ArgumentList $argument -WorkingDirectory $appDir -WindowStyle Hidden

Write-Host ""
Write-Host "Done. Press Ctrl+Alt+Shift+O, drag a screen region, and OCR text will be copied to your clipboard."
