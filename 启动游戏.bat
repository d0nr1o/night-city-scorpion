@echo off
cd /d "%~dp0"
if exist "dist\NightCityScorpion.exe" (
    start "" "dist\NightCityScorpion.exe"
) else (
    ".venv\Scripts\python.exe" main.py
    if errorlevel 1 pause
)
