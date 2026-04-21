# Quick Start - Using Your Mullvad Account ✅ UPDATED!

Your Mullvad account: `9178****3875` (saved in `vpns/vpn_config.py`)

## ✨ NEW: Mullvad API Authentication Implemented!

Your VPN tools now **automatically register WireGuard keys** with Mullvad!
- ✅ Full authentication
- ✅ Working internet through VPN
- ✅ IP address changes
- ✅ No manual config download needed!

---

## 🚀 Run Authenticated Test (RECOMMENDED)

This uses **real Mullvad API authentication** with working internet:

```bash
python tests\test_real_mullvad.py
```

**What it does:**
1. ✅ Generates WireGuard keypair
2. ✅ **Registers public key with Mullvad API**
3. ✅ Gets assigned IP from Mullvad
4. ✅ Connects with full authentication
5. ✅ **Internet works through VPN!**
6. ✅ Your IP changes to VPN location
7. ✅ Tests everything
8. ✅ Disconnects safely

**Expected result:**
- Internet keeps working ✅
- Your IP address changes ✅
- All traffic goes through VPN ✅
- **Fully authenticated with Mullvad** ✅

---

## 🧪 Safe Test Mode (No Account Needed)

To test without routing traffic:

```bash
python tests/safe_vpn_test.py
```

---

## 💻 Use in Your Code

### Full VPN with Mullvad Authentication (NEW!)

```python
from tools import connect_to_vpn, disconnect_vpn, test_vpn_connection
from vpns.vpn_config import MULLVAD_ACCOUNT

# Connect (automatically registers key with Mullvad API)
result = connect_to_vpn("fr-par-wg-001", mullvad_account=MULLVAD_ACCOUNT)

if result['success']:
    print(result['connection']['authentication'])
    # Output: "✅ WireGuard key registered with Mullvad API - Internet will work!"
    
    # Internet works! All traffic routed through VPN!
    
    # Test connection
    test = test_vpn_connection()
    if test['internet_working']:
        print(f"✅ VPN working! Current IP: {test['current_ip']} ({test['country']})")

# Disconnect when done
disconnect_vpn(force=True)
```

### Test Mode (Safe Testing)

```python
from tools import connect_to_vpn, disconnect_vpn

# Connect without routing all traffic (internet stays normal)
result = connect_to_vpn("fr-par-wg-001", test_mode=True)

# Disconnect
disconnect_vpn(force=True)
```

---

## 🔒 Security Notes

- ✅ Your account number is stored in `vpns/vpn_config.py`
- ✅ This file is in `.gitignore` (won't be committed to git)
- ✅ WireGuard config files (`.conf`) are also ignored
- ⚠️  Don't share `vpn_config.py` file publicly!

---

## 📊 Quick Commands

```python
from tools import *
from vpns.vpn_config import MULLVAD_ACCOUNT

# List servers
servers = list_vpn_servers(region="eu-west")

# Check current IP
ip = get_current_connection_info()
print(ip['current_ip'])

# Connect to first server
server_id = servers['servers'][0]['server_id']
connect_to_vpn(server_id, mullvad_account=MULLVAD_ACCOUNT)

# Test connection
test_vpn_connection()

# Disconnect
disconnect_vpn(force=True)
```

---

## ⚠️ Important

**Always run as Administrator** on Windows for VPN operations!

Right-click Python/VS Code → "Run as Administrator"
