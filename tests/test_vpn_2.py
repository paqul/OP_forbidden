import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import (
    connect_to_vpn, 
    disconnect_vpn, 
    get_current_connection_info,
)
from vpns.vpn_config import MULLVAD_ACCOUNT

# Check current IP
before = get_current_connection_info()
print(f"Before: {before['current_ip']} - {before['country']}")

# Connect with your account (full VPN, internet works!)
connect_to_vpn("fr-par-wg-001", mullvad_account=MULLVAD_ACCOUNT)

# Check new IP
after = get_current_connection_info()
print(f"After: {after['current_ip']} - {after['country']}")

# Disconnect
disconnect_vpn(force=True)