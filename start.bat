@echo off
cd /d "%~dp0"

REM Use the virtual environment if there is one (this folder or the parent folder)
if exist ".venv\Scripts\python.exe"    set "PATH=%~dp0.venv\Scripts;%PATH%"
if exist "venv\Scripts\python.exe"     set "PATH=%~dp0venv\Scripts;%PATH%"
if exist "..\.venv\Scripts\python.exe" set "PATH=%~dp0..\.venv\Scripts;%PATH%"
if exist "..\venv\Scripts\python.exe"  set "PATH=%~dp0..\venv\Scripts;%PATH%"

REM Install scikit-learn (needed for AI matching) only if it is missing
python -m pip show scikit-learn >nul 2>&1 || python -m pip install -r campuslink_backend\requirements.txt

REM Determine network IP for access from other computers
for /f "delims=" %%i in ('python -c "import socket; print(socket.gethostbyname(socket.gethostname()))" 2^>nul') do set "HOST_IP=%%i"
if "%HOST_IP%"=="" set "HOST_IP=127.0.0.1"

echo ====================================================================
echo                   Starting CampusLink System
echo ====================================================================
echo   Local computer:         http://localhost:8000/
echo   Other computers on LAN: http://%HOST_IP%:8000/
echo.
echo   ====================================================================
echo   5 DEDICATED RECRUITER LOGINS (With strict placement approval):
echo     1. TCS:      tcs@campuslink.com      Password: tcs123
echo     2. Infosys:  infosys@campuslink.com  Password: infosys123
echo     3. Wipro:    wipro@campuslink.com    Password: wipro123
echo     4. Google:   google@campuslink.com   Password: google123
echo     5. Amazon:   amazon@campuslink.com   Password: amazon123
echo.
echo   COLLEGE PLACEMENT SECTION LOGIN (Drive option + Approval workflow):
echo     College ID:  COL0001 (KIT)           Password: college123
echo.
echo   STUDENT LOGIN:
echo     Email / ID:  abhisekadhek@gmail.com (1001)  Password: student123
echo   ====================================================================

echo Starting CampusLink backend with multi-system network support...
start "CampusLink Backend" /D "%~dp0campuslink_backend" cmd /k python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

echo Waiting for the server to be ready...
timeout /t 4 /nobreak > nul

echo Opening CampusLink frontend...
start "" "http://localhost:8000/"

echo.
echo Done! Leave the "CampusLink Backend" window open while you use the app.
echo To open on another system, open a web browser and go to:
echo   http://%HOST_IP%:8000/
echo ====================================================================