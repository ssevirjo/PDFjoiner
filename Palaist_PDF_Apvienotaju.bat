@echo off
setlocal
cd /d "%~dp0"
title PDF Dokumentu Apvienotājs

if exist "PDF_Dokumentu_Apvienotajs.exe" (
    start "" "PDF_Dokumentu_Apvienotajs.exe"
    exit /b 0
)

call start.cmd
