"""
Safe VPN Testing - Test connections WITHOUT losing internet
============================================================

This script demonstrates how to safely test VPN connections using test_mode
to avoid breaking your internet connection.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import (
    list_vpn_servers,
    connect_to_vpn,
    disconnect_vpn,
    get_wireguard_status,
    test_vpn_connection,
    get_current_connection_info
)
import json


def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def print_json(data):
    print(json.dumps(data, indent=2))


def safe_vpn_test():
    """Test VPN connection safely without losing internet"""
    
    print_section("SAFE VPN CONNECTION TEST")
    print("\n⚡ This test uses TEST MODE to avoid losing internet access\n")
    
    # Step 1: Get available servers
    print_section("1. Getting Available Servers")
    servers = list_vpn_servers(region="eu-west")
    
    if not servers.get('success') or servers.get('count', 0) == 0:
        print("❌ Could not fetch servers. Check internet connection.")
        return
    
    # Pick first available server
    server = servers['servers'][0]
    server_id = server['server_id']
    print(f"✅ Selected server: {server_id} ({server['name']})")
    
    # Step 2: Check current IP BEFORE connection
    print_section("2. Current IP (Before VPN)")
    before_ip = get_current_connection_info()
    print_json(before_ip)
    
    # Step 3: Connect in TEST MODE (safe - doesn't route all traffic)
    print_section("3. Connecting in TEST MODE")
    print(f"Connecting to {server_id} with test_mode=True...")
    print("⚡ TEST MODE: Your internet will continue working!\n")
    
    result = connect_to_vpn(server_id, test_mode=True)
    print_json(result)
    
    if not result.get('success'):
        print("\n❌ Connection failed!")
        return
    
    # Step 4: Check connection status
    print_section("4. Checking Connection Status")
    import time
    time.sleep(2)
    status = get_wireguard_status()
    print_json(status)
    
    # Step 5: Test if VPN has internet access
    print_section("5. Testing VPN Internet Access")
    test_result = test_vpn_connection()
    print_json(test_result)
    
    # Step 6: Check IP AFTER connection (in test mode, might not change)
    print_section("6. Current IP (After VPN)")
    after_ip = get_current_connection_info()
    print_json(after_ip)
    
    # Step 7: Disconnect
    print_section("7. Disconnecting")
    disconnect_result = disconnect_vpn(force=True)
    print_json(disconnect_result)
    
    # Summary
    print_section("SUMMARY")
    print(f"Before VPN: {before_ip.get('current_ip')} ({before_ip.get('country')})")
    print(f"After VPN:  {after_ip.get('current_ip')} ({after_ip.get('country')})")

if __name__ == "__main__":
    # Run safe test
    safe_vpn_test()

