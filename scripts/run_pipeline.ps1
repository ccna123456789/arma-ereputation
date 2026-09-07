$ErrorActionPreference = "Stop"
& .\.venv\Scripts\Activate.ps1
python -m backend.orchestration.run_daily_pipeline
