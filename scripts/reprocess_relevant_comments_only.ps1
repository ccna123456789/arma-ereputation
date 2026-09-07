$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Environnement .venv absent. Exécutez d'abord scripts\setup_project.ps1."
}
& $python "scripts\reprocess_relevant_comments_only.py"
