@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_venomai.ps1" %*
exit /b %errorlevel%
