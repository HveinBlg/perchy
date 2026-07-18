@echo off
REM Stop every running Perchy instance regardless of how it was launched.
REM Kills BOTH python.exe (foreground / dev mode from `python main.py`)
REM AND pythonw.exe (background / run.bat / auto-start) processes whose
REM command line references main.py.
REM
REM Uses PowerShell to filter so unrelated Python scripts running from
REM other folders/venvs are left alone.

setlocal
cd /d "%~dp0"

echo Stopping Perchy...
echo.

set STOPPED=0

for /f "usebackq tokens=*" %%p in (`powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { $_.ProcessId }"`) do (
    taskkill /PID %%p /F >nul 2>&1
    if not errorlevel 1 (
        echo   Killed PID %%p
        set /A STOPPED+=1
    )
)

echo.
if %STOPPED% EQU 0 (
    echo No Perchy process was running.
    echo.
    echo If the pet is still visible, try:
    echo   - Task Manager ^(Ctrl+Shift+Esc^) -^> find python.exe / pythonw.exe -^> End Task
    echo   - Or, in the terminal running "python main.py", press Ctrl+C
) else (
    echo Perchy stopped ^(%STOPPED% process^(es^)^).
)

echo.
pause
