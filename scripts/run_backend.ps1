$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Environnement .venv introuvable. Exécutez d'abord .\scripts\setup_project.ps1"
}

& $Python -m uvicorn backend.main:app --reload
