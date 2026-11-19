@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start_VerticalFarm.ps1"
if errorlevel 1 (
    echo.
    echo Der Start ist fehlgeschlagen. Details stehen oben.
    pause
)
endlocal
