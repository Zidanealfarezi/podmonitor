@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto failed
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe main.py --demo
if errorlevel 1 goto failed
exit /b 0
:failed
echo Proses gagal. Periksa pesan galat di atas.
pause
exit /b 1
