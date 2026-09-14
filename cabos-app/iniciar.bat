@echo off
cd /d "%~dp0"
echo Instalando/atualizando dependencias...
python -m pip install -r requirements.txt
echo.
echo Iniciando o servidor em http://localhost:8000  (Ctrl+C para parar)
start "" http://localhost:8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
