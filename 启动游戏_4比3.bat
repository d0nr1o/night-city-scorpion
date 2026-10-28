@echo off
cd /d "%~dp0"
if exist "dist\NightCityScorpion.exe" (
    start "" "dist\NightCityScorpion.exe" --menu-aspect 4:3
) else (
    ".venv\Scripts\python.exe" main.py --menu-aspect 4:3
    if errorlevel 1 pause
)
