[CmdletBinding()]
param([switch]$Offline, [switch]$PrepareOnly, [switch]$Readiness)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create .venv with Python 3.11 and install requirements.txt first.' }
# Python reads all pipeline configuration; PowerShell only locates the venv.
$arguments = @('-m', 'scripts.run_pipeline')
if ($Offline) { $arguments += '--offline' }
if ($PrepareOnly) { $arguments += '--prepare-only' }
if ($Readiness) { $arguments += '--readiness' }
& $python @arguments
if ($LASTEXITCODE -ne 0) { throw "Pipeline failed with exit code $LASTEXITCODE" }
