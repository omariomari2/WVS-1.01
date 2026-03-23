@echo off
title VenomAI - OWASP Top 10 Security Scanner
echo ==========================================
echo   VenomAI - Starting up...
echo ==========================================
echo.

:: Check if backend dependencies are installed
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo [1/3] Installing backend dependencies...
    cd /d "%~dp0backend"
    pip install -e . >nul 2>&1
    cd /d "%~dp0"
    echo       Done.
) else (
    echo [1/3] Backend dependencies already installed.
)

:: Check if frontend dependencies are installed
if not exist "%~dp0frontend\node_modules" (
    echo [2/3] Installing frontend dependencies...
    cd /d "%~dp0frontend"
    npm install >nul 2>&1
    cd /d "%~dp0"
    echo       Done.
) else (
    echo [2/3] Frontend dependencies already installed.
)

echo [3/3] Starting servers...
echo.

:: Start backend in a new window
start "VenomAI Backend" cmd /k "cd /d %~dp0backend && uvicorn app.main:app --reload --port 8000"

:: Wait for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend in a new window
start "VenomAI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

:: Wait for frontend to start
timeout /t 5 /nobreak >nul

:: Open browser
echo.
echo ==========================================
echo   VenomAI is running!
echo   Opening http://localhost:3000 ...
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo.
echo   Close this window to stop both servers.
echo ==========================================
start http://localhost:3000

:: Keep this window open - closing it won't stop the servers
:: The servers run in their own windows
pause
