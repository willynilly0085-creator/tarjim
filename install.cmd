@echo off
rem Double-click this file to install tarjim and start it. What it does is in scripts\windows\install.ps1.
title tarjim
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\install.ps1" %*
echo.
pause
