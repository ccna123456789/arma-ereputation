$ErrorActionPreference = "Stop"

if (Get-Command n8n -ErrorAction SilentlyContinue) {
    n8n start
    exit $LASTEXITCODE
}

if (Get-Command npx -ErrorAction SilentlyContinue) {
    Write-Host "n8n n'est pas installé globalement. Lancement avec npx..."
    npx n8n
    exit $LASTEXITCODE
}

throw "Node.js/npm est requis pour lancer n8n."
