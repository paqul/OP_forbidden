"""
Safe VPN Testing - Test connections WITHOUT losing internet
============================================================

This script demonstrates how to safely test VPN connections using test_mode
to avoid breaking your internet connection.
"""

import sys
import os
import time
import json
import ctypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keys.projects_api_keys import MULLVAD_ACCOUNT
from vpn_tools import (
    list_vpn_servers,
    connect_to_vpn,
    disconnect_vpn,
    get_wireguard_status,
    test_vpn_connection,
    get_current_connection_info
)


def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def print_json(data):
    print(json.dumps(data, indent=2))


def is_admin():
    """Check if script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def safe_vpn_test():
    """Test VPN connection with Mullvad authentication"""
    
    print_section("MULLVAD VPN CONNECTION TEST")
    print("\n🔒 This test connects with Mullvad authentication (PRODUCTION MODE)")
    print("⚠️  Your traffic will be routed through VPN and your IP will change!\n")
    
    # Check admin privileges
    if not is_admin():
        print("❌ ERROR: Administrator privileges required!")
        print("   Please run this script as Administrator:")
        print("   1. Right-click Python or your IDE")
        print("   2. Select 'Run as Administrator'")
        print("   3. Run this script again")
        return
    
    print("✅ Running with Administrator privileges\n")
    
    # Step 1: Get available servers
    print_section("1. Getting Available Servers")
    servers = list_vpn_servers(region="eu-west")
    
    if not servers.get('success') or servers.get('count', 0) == 0:
        print("❌ Could not fetch servers. Check internet connection.")
        print_json(servers)
        return
    
    # Pick first available server
    server = servers['servers'][0]
    server_id = server['server_id']
    print(f"✅ Selected server: {server_id} ({server['name']})")
    
    # Step 2: Check current IP BEFORE connection
    print_section("2. Current IP (Before VPN)")
    before_ip = get_current_connection_info()
    print_json(before_ip)
    
    if not before_ip.get('success'):
        print("⚠️  Warning: Could not get current IP")
    
    # Step 3: Connect with Mullvad account (production mode)
    print_section("3. Connecting with Mullvad Account")
    print(f"Connecting to {server_id} with test_mode=False...")
    print("🔒 PRODUCTION MODE: Authenticating with Mullvad account")
    print("⚠️  All traffic will be routed through VPN - your IP will change!\n")
    
    result = connect_to_vpn(server_id, mullvad_account=MULLVAD_ACCOUNT, test_mode=False)

    print_json(result)
    
    if not result.get('success'):
        print("\n❌ Connection failed!")
        return
    
    # Step 4: Check connection status
    print_section("4. Checking Connection Status")
    time.sleep(2)
    status = get_wireguard_status()
    print_json(status)
    
    if not status.get('connected'):
        print("⚠️  Warning: Tunnel status shows not connected")
    
    # Step 5: Test if VPN has internet access
    print_section("5. Testing VPN Internet Access")
    test_result = test_vpn_connection()
    print_json(test_result)
    
    if not test_result.get('success'):
        print("⚠️  Warning: VPN tunnel test failed")
    
    # Step 6: Check IP AFTER connection (in test mode, might not change)
    print_section("6. Current IP (After VPN)")
    after_ip = get_current_connection_info()
    print_json(after_ip)
    
    if not after_ip.get('success'):
        print("⚠️  Warning: Could not get current IP after connection")
    
    # Step 7: Disconnect
    print_section("7. Disconnecting")
    disconnect_result = disconnect_vpn(force=True)
    print_json(disconnect_result)
    
    if not disconnect_result.get('success'):
        print("⚠️  Warning: Disconnect may have failed")
    
    # Summary
    print_section("SUMMARY")
    
    # Safely extract IP info
    before_ip_addr = before_ip.get('current_ip', 'Unknown') if before_ip.get('success') else 'Unavailable'
    before_country = before_ip.get('country', 'Unknown') if before_ip.get('success') else 'Unavailable'
    after_ip_addr = after_ip.get('current_ip', 'Unknown') if after_ip.get('success') else 'Unavailable'
    after_country = after_ip.get('country', 'Unknown') if after_ip.get('success') else 'Unavailable'
    
    print(f"Before VPN: {before_ip_addr} ({before_country})")
    print(f"After VPN:  {after_ip_addr} ({after_country})")
    
    if before_ip_addr == after_ip_addr:
        print("\n⚠️  WARNING: IP didn't change - VPN may not be routing traffic properly!")
        print("   In production mode with Mullvad account, IP should change.")
        print("   Check if WireGuard tunnel is active and configured correctly.")
    else:
        print("\n✅ SUCCESS: IP changed - VPN is routing all traffic!")
        print(f"   Your traffic is now routed through: {after_country}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    # Run safe test
    safe_vpn_test()

