$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $Python = "python"
    } else {
        throw "Python est introuvable."
    }
}

& $Python -m http.server 5500 --directory frontend
