@echo off
setlocal
cd /d "%~dp0"
title PDF Document Joiner

echo ========================================================
echo         PDF Document Joiner (PDF, DOCX, JPG)
echo ========================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH!
    echo [OSHIBKA] Python ne naiden! Ustanovite Python 3 s python.org
    pause
    exit /b 1
)

echo Starting application on port 3335...
python run.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application terminated with error.
    pause
)
