@echo off
setlocal enableextensions

REM Robust one-click start: launch tracker (tray) and GUI
REM Works with system Python; prints helpful errors if failing.

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
pushd "%ROOT%" || (
  echo Failed to change to script directory.
  goto :end
)

REM Detect Python (prefer venv)
set "VENV_PY=%ROOT%\.venv\Scripts\python.exe"
set "VENV_PYW=%ROOT%\.venv\Scripts\pythonw.exe"
set "PYEXE="
if exist "%VENV_PYW%" (
  set "PYEXE=%VENV_PYW%"
) else if exist "%VENV_PY%" (
  set "PYEXE=%VENV_PY%"
) else (
  REM Prefer pythonw on PATH, else python
  for /f "usebackq tokens=*" %%P in (`where pythonw 2^>nul`) do (
    if not defined PYEXE set "PYEXE=%%P"
  )
  if not defined PYEXE (
    for /f "usebackq tokens=*" %%P in (`where python 2^>nul`) do (
      if not defined PYEXE set "PYEXE=%%P"
    )
  )
)
if not defined PYEXE (
  echo Python not found. Please install Python or create .venv.
  goto :end
)

REM Ensure data dir exists
if not exist "%ROOT%\data" mkdir "%ROOT%\data" >nul 2>nul

REM Launch tracker (minimized)
echo Starting tracker (tray)...
start "Tracker" /min "%PYEXE%" "%ROOT%\tracker.py"
if errorlevel 1 echo Warning: tracker may not have started.

REM Launch GUI (force via python to avoid .pyw association issues)
echo Starting GUI...
if exist "%ROOT%\app.pyw" (
  start "GUI" "%PYEXE%" "%ROOT%\app.pyw"
) else if exist "%ROOT%\app.py" (
  start "GUI" "%PYEXE%" "%ROOT%\app.py"
) else (
  echo GUI script not found (app.pyw/app.py).
)

:end
popd >nul 2>nul
endlocal
exit /b 0
