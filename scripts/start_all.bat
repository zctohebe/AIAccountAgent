@echo off
REM One-click start for backend, frontend, and local scheduler (opens three cmd windows)
REM Location: scripts\start_all.bat (run from repository root or scripts folder)

SETLOCAL EnableDelayedExpansion

:: Resolve repository root (parent of scripts folder)
PUSHD "%~dp0.."
SET "ROOT=%CD%"

:: Ensure python exists on PATH
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python is not found on PATH. Please install Python 3.9+ and add to PATH.
    POPD
    ENDLOCAL
    pause
    exit /b 1
)

:: Backend venv handling - create venv only if it does not already exist
SET "VENV=%ROOT%\backend\.venv"
SET "PYEXEC=%VENV%\Scripts\python.exe"
IF NOT EXIST "%PYEXEC%" (
    echo Virtual environment not found at %VENV% - creating .venv ...
    python -m venv "%VENV%" || (
        echo Failed to create virtual environment
        POPD
        ENDLOCAL
        pause
        exit /b 1
    )
)

:: Ensure PYEXEC points to the venv python (whether just created or pre-existing)
SET "PYEXEC=%VENV%\Scripts\python.exe"
IF NOT EXIST "%PYEXEC%" (
    echo venv python not found at %PYEXEC%. Aborting.
    POPD
    ENDLOCAL
    pause
    exit /b 1
)

:: Check whether required packages are installed in the venv; if not, install only the missing packages
SET "MISSING_PKGS="

"%PYEXEC%" -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('boto3') else 1)" 2>nul
IF ERRORLEVEL 1 (
    echo 'boto3' not found in venv.
    if defined MISSING_PKGS ( set "MISSING_PKGS=%MISSING_PKGS% boto3" ) else set "MISSING_PKGS=boto3"
)

"%PYEXEC%" -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('requests') else 1)" 2>nul
IF ERRORLEVEL 1 (
    echo 'requests' not found in venv.
    if defined MISSING_PKGS ( set "MISSING_PKGS=%MISSING_PKGS% requests" ) else set "MISSING_PKGS=requests"
)

"%PYEXEC%" -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('apscheduler') else 1)" 2>nul
IF ERRORLEVEL 1 (
    echo 'APScheduler' not found in venv.
    if defined MISSING_PKGS ( set "MISSING_PKGS=%MISSING_PKGS% apscheduler" ) else set "MISSING_PKGS=apscheduler"
)

IF DEFINED MISSING_PKGS (
    echo Installing missing Python packages:%MISSING_PKGS%
    "%PYEXEC%" -m pip install --upgrade pip
    "%PYEXEC%" -m pip install %MISSING_PKGS%
) ELSE (
    echo 'boto3', 'requests' and 'apscheduler' already installed in venv.
)

IF EXIST "%ROOT%\backend\requirements.txt" (
    echo Installing backend requirements from requirements.txt...
    "%PYEXEC%" -m pip install -r "%ROOT%\backend\requirements.txt"
)

:: Start backend in new cmd window (no nested IF blocks)
echo Starting backend (new window)...
START "Backend" cmd /k cd /d "%ROOT%" ^& "%PYEXEC%" backend\handler.py

:: Start frontend (single-line IF)
IF EXIST "%ROOT%\frontend" START "Frontend" cmd /k cd /d "%ROOT%\frontend" ^& python -m http.server 8080

:: Start local scheduler (single-line IF)
IF EXIST "%ROOT%\scripts\local_scheduler.py" START "Scheduler" cmd /k cd /d "%ROOT%" ^& "%PYEXEC%" scripts\local_scheduler.py

POPD
ENDLOCAL
