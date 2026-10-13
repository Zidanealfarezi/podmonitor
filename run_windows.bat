@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto failed
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe main.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Proses gagal. Pastikan Python 3.11 atau lebih baru terpasang.
echo Lihat pesan galat di atas dan README.md.
pause
exit /b 1
