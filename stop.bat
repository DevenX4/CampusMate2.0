@echo off
title Stopping services
color 0C
cls

set "APP_DIR=%~dp0"
if exist "%~dp0CampusMate_2-main\package.json" set "APP_DIR=%~dp0CampusMate_2-main\"

node "%APP_DIR%scripts\launch.mjs" --stop
taskkill /FI "IMAGENAME eq cmd.exe" /FI "WINDOWTITLE eq CampusMate 2.0 - Running*" /F >nul 2>nul

powershell -NoProfile -Command "Start-Sleep -Seconds 2" >nul 2>nul
exit /b 0
