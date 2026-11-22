@echo off
title CampusMate 2.0 - Running
color 0B
cls

echo ======================================================================
echo                         CAMPUSMATE 2.0
echo ======================================================================
echo.

set "APP_DIR=%~dp0"
if exist "%~dp0CampusMate_2-main\package.json" set "APP_DIR=%~dp0CampusMate_2-main\"
cd /d "%APP_DIR%"

where node >nul 2>nul
if errorlevel 1 (
    color 0C
    echo [ERROR] Node.js is not installed or not in PATH.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    color 0C
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

node "%APP_DIR%scripts\launch.mjs" %*
if errorlevel 1 (
    color 0C
    echo.
    echo CampusMate could not start. Read the message above.
    pause
)
