@echo off
cd /d "%~dp0"

REM Use the virtual environment if there is one (this folder or the parent folder)
if exist ".venv\Scripts\python.exe"    set "PATH=%~dp0.venv\Scripts;%PATH%"
if exist "venv\Scripts\python.exe"     set "PATH=%~dp0venv\Scripts;%PATH%"
if exist "..\.venv\Scripts\python.exe" set "PATH=%~dp0..\.venv\Scripts;%PATH%"
if exist "..\venv\Scripts\python.exe"  set "PATH=%~dp0..\venv\Scripts;%PATH%"

REM Install scikit-learn (needed for AI matching) only if it is missing
python -m pip show scikit-learn >nul 2>&1 || python -m pip install -r campuslink_backend\requirements.txt

echo Starting CampusLink backend...
start "CampusLink Backend" /D "%~dp0campuslink_backend" cmd /k python -m uvicorn main:app --reload

echo Waiting for the server to be ready...
timeout /t 5 /nobreak > nul

echo Opening CampusLink frontend...
start "" "%~dp0campuslink_frontend\campuslink_frontend\index.html"

echo Done. Leave the "CampusLink Backend" window open while you use the app.