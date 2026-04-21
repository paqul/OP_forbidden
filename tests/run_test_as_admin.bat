@echo off
REM WireGuard VPN Test - Run with Administrator Privileges
REM This script automatically requests admin elevation

echo ============================================
echo  WireGuard VPN Tools Test (Admin Mode)
echo ============================================
echo.

REM Check if already running as admin
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as Administrator
    echo.
    python "%~dp0test_vpn_1.py"
    pause
) else (
    echo Requesting Administrator privileges...
    echo.
    powershell -Command "Start-Process python -ArgumentList '%~dp0test_vpn_1.py' -Verb RunAs"
)
