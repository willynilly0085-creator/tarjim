@echo off
rem Copies the tarjim security token to the clipboard for the browser extension.
"%~dp0..\..\.venv\Scripts\python.exe" -m tarjim.server --show-token | clip
echo Token copied. Paste it in the tarjim extension.
timeout /t 4 >nul
