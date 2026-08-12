$ErrorActionPreference = "Stop"
if (-not (Test-Path "src\kynka")) { throw "Execute na raiz do projeto Kynka." }
python -m pip install -r requirements-api.txt
python -m pip install -e .
python -c "from kynka.presentation.api import app; print('API:', app.title)"
python -m pytest tests\api -q
Write-Host ""
Write-Host "Backend preparado." -ForegroundColor Green
Write-Host "Inicie: python run_api.py"
Write-Host "Swagger: http://127.0.0.1:8000/docs"
