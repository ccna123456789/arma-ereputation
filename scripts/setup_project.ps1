$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Fichier .env créé. Renseignez DATABASE_URL et SERPER_API_KEY avant de continuer." -ForegroundColor Yellow
    exit 0
}

python -m alembic upgrade head
python -m backend.database.seed
python -m backend.database.seed_rss_sources
python -m backend.processing.qualify_existing_mentions
Write-Host "Installation terminée." -ForegroundColor Green
