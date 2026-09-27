@echo off
REM start.bat — launches CampusLink backend + frontend together.
REM Place this file directly inside the "campuslink" folder,
REM as a sibling of campuslink_backend and campuslink_frontend.

echo Starting CampusLink backend...
start "CampusLink Backend" cmd /k "cd /d %~dp0campuslink_backend && python -m uvicorn main:app --reload"

echo Waiting for the server to be ready...
timeout /t 4 /nobreak > nul

echo Opening CampusLink frontend...
start "" "%~dp0campuslink_frontend\campuslink_frontend\index.html"

echo Done. Leave the "CampusLink Backend" window open while you use the app.
