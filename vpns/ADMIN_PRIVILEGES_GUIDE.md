# Running VPN Tests with Administrator Privileges

## Problem
WireGuard requires **Administrator privileges** on Windows to install and manage VPN tunnels. Without admin rights, you'll see this error:

```
"error": "Administrator privileges required. Please run Python as Administrator."
```

## Solutions

### Option 1: Run PowerShell Script (Easiest)
Double-click this file to automatically run with admin:
```
tests/run_test_as_admin.ps1
```

Or in PowerShell:
```powershell
cd D:\Python_Projects\OP_forbidden\tests
.\run_test_as_admin.ps1
```

### Option 2: Run Batch File
Double-click this file:
```
tests/run_test_as_admin.bat
```

### Option 3: Run Python as Administrator Manually

#### From Command Prompt/PowerShell:
1. **Right-click** on PowerShell/Command Prompt
2. Select **"Run as Administrator"**
3. Navigate to project:
   ```powershell
   cd D:\Python_Projects\OP_forbidden
   ```
4. Run test:
   ```powershell
   python tests\test_vpn_1.py
   ```

#### From VS Code:
1. Close VS Code
2. **Right-click** VS Code icon
3. Select **"Run as Administrator"**
4. Open your project
5. Run the test normally

### Option 4: Run Python Directly as Admin
```powershell
Start-Process python -ArgumentList "tests\test_vpn_1.py" -Verb RunAs -WorkingDirectory "D:\Python_Projects\OP_forbidden"
```

## What You'll See With Admin Rights

✅ **With Admin:**
```json
{
  "running_as_admin": true,
  "can_manage_tunnels": true,
  "note": "Running with admin privileges"
}
```

❌ **Without Admin:**
```json
{
  "running_as_admin": false,
  "can_manage_tunnels": false,
  "note": "Administrator privileges required for tunnel management"
}
```

## Why Admin Is Required

WireGuard needs admin privileges to:
- Install tunnel services (`/installtunnelservice`)
- Start/stop VPN connections (`/start`, `/stop`)
- Modify network routing tables
- Uninstall tunnel services (`/uninstalltunnelservice`)

## What Works WITHOUT Admin

These functions work without admin privileges:
- ✅ `list_vpn_servers()` - List available servers
- ✅ `get_vpn_server_status()` - Get server details
- ✅ `get_current_connection_info()` - Check your IP
- ✅ `check_wireguard_installation()` - Verify installation
- ✅ `list_configured_tunnels()` - List configs
- ✅ `get_wireguard_status()` - Check connection status

These require admin:
- ❌ `connect_to_vpn()` - Connect to VPN
- ❌ `disconnect_vpn()` - Disconnect from VPN

## Testing the Fix

Run the test and check the first output:

```bash
python tests\test_vpn_1.py
```

Look for:
```
⚠️  WARNING: Not running as Administrator!
   Connection/disconnection tests will FAIL without admin rights.
   To fix: Right-click Python/VS Code → 'Run as Administrator'
```

If you see ✅ instead, you're running with admin privileges!
