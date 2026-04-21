# WireGuard VPN Test - PowerShell Admin Launcher
# This script automatically elevates to administrator if needed

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " WireGuard VPN Tools Test (Admin Mode)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    Write-Host "[OK] Running as Administrator" -ForegroundColor Green
    Write-Host ""
    
    # Get the script directory
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    $testScript = Join-Path $scriptPath "test_vpn_1.py"
    
    # Run the Python test
    python $testScript
    
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} else {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Write-Host ""
    
    # Get the script directory and test script path
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    $testScript = Join-Path $scriptPath "test_vpn_1.py"
    
    # Restart this script with elevation
    Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-Command", "cd '$scriptPath'; python test_vpn_1.py; Write-Host ''; Write-Host 'Press any key to exit...'; `$null = `$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')"
}
