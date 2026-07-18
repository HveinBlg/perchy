@echo off
REM Launch Perchy in the background without a console window.
REM Double-click this file to run the pet, or put a shortcut to it in
REM your Startup folder (see README) to auto-launch at login.
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "Perchy" ".venv\Scripts\pythonw.exe" main.py
) else (
    start "Perchy" pythonw main.py
)
exit
