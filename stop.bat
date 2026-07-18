@echo off
REM Stop every running instance of Perchy (kills all pythonw.exe processes
REM whose command line references main.py under this project).
REM Uses WMIC so we don't nuke unrelated pythonw processes.
for /f "tokens=2 delims==" %%i in ('wmic process where "name='pythonw.exe' and commandline like '%%main.py%%'" get processid /value ^| find "="') do (
    taskkill /PID %%i /F >nul 2>&1
)
echo Perchy stopped.
