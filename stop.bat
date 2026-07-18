@echo off
REM Universal Perchy stopper. Kills every kind of Perchy process, in
REM order of most-likely-first:
REM
REM   1. perchy.exe   -- the PyInstaller-packaged binary shipped in
REM                      GitHub Release zips. This bat also lives inside
REM                      those zips, so it must handle its own process
REM                      name.
REM   2. python.exe   -- someone running `python main.py` in a terminal
REM                      (foreground / dev mode).
REM   3. pythonw.exe  -- someone running `run.bat` (background) or
REM                      auto-started via Startup folder shortcut.
REM
REM For python.exe / pythonw.exe we filter by CommandLine LIKE '*main.py*'
REM so unrelated Python scripts on the system are left alone. perchy.exe
REM is safe to kill by name because it's only ever created by PyInstaller
REM as the frozen Perchy binary.

setlocal
cd /d "%~dp0"

echo Stopping Perchy...
echo.

set STOPPED=0

REM ---- 1) packaged perchy.exe (from Release zips) ---------------------
for /f "usebackq tokens=1" %%p in (`powershell -NoProfile -Command "Get-Process -Name perchy -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }"`) do (
    taskkill /PID %%p /F /T >nul 2>&1
    if not errorlevel 1 (
        echo   Killed perchy.exe PID %%p
        set /A STOPPED+=1
    )
)

REM ---- 2) source-mode python.exe / pythonw.exe running main.py --------
for /f "usebackq tokens=*" %%p in (`powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { $_.ProcessId }"`) do (
    taskkill /PID %%p /F >nul 2>&1
    if not errorlevel 1 (
        echo   Killed python PID %%p
        set /A STOPPED+=1
    )
)

echo.
if %STOPPED% EQU 0 (
    echo No Perchy process was running.
    echo.
    echo If the pet is still visible, try:
    echo   - Task Manager ^(Ctrl+Shift+Esc^) -^> Details tab
    echo     -^> find perchy.exe / python.exe / pythonw.exe -^> End Task
    echo   - Or, in the terminal running "python main.py", press Ctrl+C
) else (
    echo Perchy stopped ^(%STOPPED% process^(es^)^).
)

echo.
pause
