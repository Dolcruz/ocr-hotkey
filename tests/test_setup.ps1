$ErrorActionPreference = "Stop"
$setupPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Setup-OcrHotkey.ps1"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($setupPath, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw "Setup script has syntax errors." }
$resolver = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq "Resolve-Python" }, $true)
Invoke-Expression $resolver.Extent.Text

# Simulate installed launchers that exit unsuccessfully, then a supported Python.
function py { $global:LASTEXITCODE = 1 }
function python { $global:LASTEXITCODE = 0 }
$result = Resolve-Python
if ($result.Command -ne "python") { throw "An unsupported Python launcher was accepted." }
Write-Host "PASS: unsuccessful launchers are skipped."

function python { $global:LASTEXITCODE = 1 }
$rejected = $false
try { Resolve-Python | Out-Null } catch { $rejected = $true }
if (-not $rejected) { throw "Setup accepted an environment with no supported Python." }
Write-Host "PASS: setup rejects environments without Python 3.11 or 3.12."
