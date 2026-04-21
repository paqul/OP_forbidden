# WireGuard VPN Tools - Usage Guide

## ✅ What's Been Updated

Your VPN tools in `tools.py` now **actually connect** to WireGuard VPN servers instead of just simulating connections!

### Updated Functions

1. **`connect_to_vpn(server_id, protocol="wireguard", mullvad_account=None)`**
   - Creates real WireGuard config files
   - Installs and activates tunnels
   - Supports optional Mullvad account for authentication

2. **`disconnect_vpn(force=False)`**
   - Disconnects active WireGuard tunnel
   - `force=True` removes tunnel completely

3. **`get_wireguard_status()`**
   - Returns current WireGuard connection status
   - Shows active tunnel name if connected

4. **`list_configured_tunnels()`**
   - Lists all WireGuard configurations on your system

5. **`check_wireguard_installation()`**
   - Verifies WireGuard is properly installed
   - Shows paths and version info

## 🚀 Quick Start

### 1. Test Installation
```python
from tools import check_wireguard_installation

status = check_wireguard_installation()
print(status)
```

### 2. List Available Servers
```python
from tools import list_vpn_servers

# Get all servers
servers = list_vpn_servers()

# Get servers by region
eu_servers = list_vpn_servers(region="eu-west")
us_servers = list_vpn_servers(region="us-east")
```

### 3. Get Server Details
```python
from tools import get_vpn_server_status

server_info = get_vpn_server_status("fr-par-wg-001")
print(server_info)
```

### 4. Check Your Current IP
```python
from tools import get_current_connection_info

ip_info = get_current_connection_info()
print(f"Your IP: {ip_info['current_ip']}")
print(f"Country: {ip_info['country']}")
```

### 5. Connect to VPN
```python
from tools import connect_to_vpn

# Basic connection (creates config, may not authenticate)
result = connect_to_vpn("fr-par-wg-001")

# With Mullvad account (for full authentication)
result = connect_to_vpn("fr-par-wg-001", mullvad_account="YOUR_ACCOUNT_NUMBER")
print(result)
```

### 6. Check Connection Status
```python
from tools import get_wireguard_status

status = get_wireguard_status()
if status['connected']:
    print(f"Connected to: {status['tunnel_name']}")
else:
    print("Not connected")
```

### 7. Disconnect
```python
from tools import disconnect_vpn

# Normal disconnect (keeps config)
result = disconnect_vpn()

# Force disconnect (removes config)
result = disconnect_vpn(force=True)
```

## 📝 Important Notes

### Mullvad Account
- **Without Account**: Config files are created with valid structure, but won't authenticate
- **With Account**: Full VPN functionality works
- Get an account at: https://mullvad.net/

### Configuration Files
- Stored in: `%LocalAppData%\WireGuard\Configurations\`
- Named as: `{server_id}.conf`
- Each connection generates a new keypair

### Server Regions
Available region filters:
- `us-east` - Eastern USA
- `us-west` - Western USA
- `eu-west` - UK/Netherlands/France/Poland
- `eu-central` - Germany/Switzerland/Austria
- `asia-pacific` - Japan/Singapore/Australia/Hong Kong
- `all` - Worldwide (default)

## 🧪 Running Tests

Run the comprehensive test suite:
```bash
python tests/test_vpn_1.py
```

This will test:
1. ✅ WireGuard installation
2. ✅ Server listing
3. ✅ Server status lookup
4. ✅ Current IP detection
5. ✅ Connection status check
6. ✅ Tunnel configuration listing

To test actual connection, uncomment the line in the test file as indicated.

## 🛠️ WireGuard Commands Used

The tools use these WireGuard CLI commands internally:
- `wg genkey` - Generate private key
- `wg pubkey` - Generate public key
- `wireguard.exe /installtunnelservice <config>` - Install tunnel
- `wireguard.exe /start <tunnel_name>` - Start connection
- `wireguard.exe /stop <tunnel_name>` - Stop connection
- `wireguard.exe /uninstalltunnelservice <tunnel_name>` - Remove tunnel
- `wireguard.exe /tunnelstatus` - Check status

## 📁 File Locations

- **WireGuard CLI**: `C:\Program Files\WireGuard\wg.exe`
- **WireGuard GUI**: `C:\Program Files\WireGuard\wireguard.exe`
- **Config Directory**: `C:\Users\{username}\AppData\Local\WireGuard\Configurations\`

## 🔒 Security Notes

- Private keys are generated fresh for each connection
- Config files contain sensitive keys - don't share them
- Disconnect when done to avoid unwanted routing
- Use `force=True` disconnect to clean up configs

## 💡 Example Workflow

```python
from tools import *

# 1. Check installation
print(check_wireguard_installation())

# 2. Find a server
servers = list_vpn_servers(region="eu-west")
server_id = servers['servers'][0]['server_id']

# 3. Check current IP
before = get_current_connection_info()
print(f"Before: {before['current_ip']} - {before['country']}")

# 4. Connect
connect_to_vpn(server_id)

# 5. Verify connection
status = get_wireguard_status()
print(f"Status: {status}")

# 6. Check new IP (after connection established)
import time
time.sleep(3)  # Wait for connection
after = get_current_connection_info()
print(f"After: {after['current_ip']} - {after['country']}")

# 7. Disconnect
disconnect_vpn(force=True)
```

## ❓ Troubleshooting

**Connection fails:**
- Requires Mullvad account for authentication
- Check firewall settings
- Verify WireGuard service is running

**Can't find servers:**
- Check internet connection
- Mullvad API might be temporarily down

**Config not created:**
- Check permissions on config directory
- Run as administrator if needed

**Already connected error:**
- Disconnect first: `disconnect_vpn()`
- Or force disconnect: `disconnect_vpn(force=True)`
