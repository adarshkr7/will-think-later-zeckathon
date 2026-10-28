[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
& $python -m scripts.serve_app
if ($LASTEXITCODE -ne 0) { throw "App exited with code $LASTEXITCODE" }
