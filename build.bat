@echo off
REM Build a self-contained Windows folder that end-users can just
REM download and double-click, no Python required. Uses PyInstaller.
REM
REM Usage:  double-click this file, or run it in a terminal.
REM Output: dist\perchy\perchy.exe  (+ assets, 使用说明.txt, stop.bat)
REM Zip:    powershell Compress-Archive -Path dist\perchy -DestinationPath perchy-windows-x64.zip -Force

setlocal
cd /d "%~dp0"

echo === Perchy build ===
echo.

REM ---- venv ----
if not exist ".venv\Scripts\python.exe" (
    echo Creating .venv with default Python...
    py -3 -m venv .venv || goto :err
)
call ".venv\Scripts\activate.bat"

REM ---- deps ----
python -m pip install --upgrade pip >nul
pip install -q -r requirements.txt pyinstaller || goto :err

REM ---- clean ----
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM ---- build ----
REM --windowed  = no console window
REM --noupx     = don't compress with UPX (helps avoid AV false positives)
REM --onedir    = one folder (default), users can browse assets/pets
pyinstaller --clean --noconfirm ^
    --name perchy ^
    --windowed ^
    --noupx ^
    main.py || goto :err

REM ---- copy user-facing files next to the exe ----
xcopy /E /I /Y assets dist\perchy\assets >nul
if exist "使用说明.txt" copy /Y "使用说明.txt" dist\perchy\ >nul
if exist USAGE.txt      copy /Y USAGE.txt      dist\perchy\ >nul
if exist stop.bat       copy /Y stop.bat       dist\perchy\ >nul

echo.
echo === Build complete ===
echo Output: dist\perchy\perchy.exe
echo.
echo To share, zip the whole folder:
echo   powershell Compress-Archive -Path dist\perchy -DestinationPath perchy-windows-x64.zip -Force
goto :eof

:err
echo.
echo BUILD FAILED
exit /b 1
