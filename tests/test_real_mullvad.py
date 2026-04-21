"""
Real Mullvad Account Test - WITH API AUTHENTICATION
===================================================

This test uses your Mullvad account with FULL API authentication.
Your WireGuard key will be registered with Mullvad, enabling working internet!
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
from vpns.vpn_config import MULLVAD_ACCOUNT
import json
import time


def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def print_json(data):
    print(json.dumps(data, indent=2))


def authenticated_vpn_test():
    """Test VPN with Mullvad API authentication - Full working internet!"""
    
    print_section("🔒 MULLVAD VPN - AUTHENTICATED CONNECTION TEST")
    print(f"\n✅ Using Mullvad account: {MULLVAD_ACCOUNT[:4]}****{MULLVAD_ACCOUNT[-4:]}")
    print("✅ WireGuard key will be registered via Mullvad API")
    print("✅ Internet will work through VPN!")
    print("✅ Your IP will change to VPN server location\n")
    
    # Step 1: Get available servers
    print_section("1. Getting Available Servers")
    servers = list_vpn_servers(region="eu-west")
    
    if not servers.get('success') or servers.get('count', 0) == 0:
        print("❌ Could not fetch servers. Check internet connection.")
        return
    
    # Show first 5 servers
    print(f"\n✅ Found {servers['count']} servers. Top 5:")
    for i, server in enumerate(servers['servers'][:5], 1):
        print(f"  {i}. {server['server_id']:20} - {server['name']:30} ({server['provider']})")
    
    # Pick first available server
    server = servers['servers'][0]
    server_id = server['server_id']
    print(f"\n🎯 Selected: {server_id} ({server['name']})")
    
    # Step 2: Check current IP BEFORE connection
    print_section("2. Current IP BEFORE VPN")
    before_ip = get_current_connection_info()
    if before_ip.get('success'):
        print(f"IP:      {before_ip['current_ip']}")
        print(f"Country: {before_ip['country']}")
        print(f"ISP:     {before_ip['isp']}")
    else:
        print_json(before_ip)
    
    # Step 3: Connect with Mullvad account (AUTHENTICATED)
    print_section("3. Connecting to VPN - AUTHENTICATED MODE")
    print(f"🔒 Connecting to {server_id}...")
    print("⚡ Registering WireGuard key with Mullvad API...")
    print("⚡ All traffic will be routed through VPN\n")
    
    result = connect_to_vpn(server_id, mullvad_account=MULLVAD_ACCOUNT)
    print_json(result)
    
    if not result.get('success'):
        print("\n❌ Connection failed!")
        print("Possible issues:")
        print("  - Invalid account number")
        print("  - Account has no credit (needs payment)")
        print("  - Mullvad API is down")
        return
    
    # Check authentication status
    if result.get('connection', {}).get('authenticated'):
        print("\n🎉 SUCCESS! Authenticated with Mullvad API!")
    else:
        print("\n⚠️  Warning: Connection succeeded but authentication unclear")
    
    # Step 4: Wait for connection to establish
    print_section("4. Waiting for Connection to Establish")
    print("Waiting 5 seconds for tunnel to activate...")
    time.sleep(5)
    
    status = get_wireguard_status()
    if status.get('connected'):
        print(f"✅ Connected to: {status['tunnel_name']}")
    else:
        print("⚠️  Status check:")
        print_json(status)
    
    # Step 5: Test VPN internet access
    print_section("5. Testing VPN Internet Access")
    print("Testing if authenticated VPN has working internet...")
    test_result = test_vpn_connection()
    print_json(test_result)
    
    if test_result.get('internet_working'):
        print("\n🎉 SUCCESS! VPN has working internet access!")
        print("✅ Mullvad authentication is working correctly!")
    else:
        print("\n⚠️  VPN tunnel active but internet test failed")
        print("This might mean:")
        print("  - Account has no credit")
        print("  - Network is still establishing")
        print("  - Wait a few more seconds and try again")
    
    # Step 6: Check IP AFTER connection
    print_section("6. Current IP AFTER VPN")
    print("Checking IP through authenticated VPN tunnel...")
    time.sleep(2)  # Extra wait for DNS to work
    after_ip = get_current_connection_info()
    if after_ip.get('success'):
        print(f"IP:      {after_ip['current_ip']}")
        print(f"Country: {after_ip['country']}")
        print(f"ISP:     {after_ip['isp']}")
    else:
        print("⚠️  Could not fetch IP (may still be connecting):")
        print_json(after_ip)
    
    # Step 7: Compare before/after
    print_section("7. IP CHANGE VERIFICATION")
    if before_ip.get('success') and after_ip.get('success'):
        before = before_ip['current_ip']
        after = after_ip['current_ip']
        
        print(f"Before VPN: {before:20} ({before_ip['country']})")
        print(f"After VPN:  {after:20} ({after_ip['country']})")
        
        if before != after:
            print("\n🎉 SUCCESS! Your IP address changed!")
            print(f"   Old location: {before_ip['country']}")
            print(f"   New location: {after_ip['country']}")
            print("   ✅ VPN is routing your traffic!")
        else:
            print("\n⚠️  IP did not change")
            print("   Possible reasons:")
            print("   - Tunnel still connecting (wait longer)")
            print("   - Account authentication issue")
    else:
        print("\n⚠️  Cannot compare IPs (at least one check failed)")
    
    # Step 8: Disconnect
    print("\n\n" + "="*70)
    input("Press ENTER to disconnect from VPN...")
    
    print_section("8. Disconnecting from VPN")
    disconnect_result = disconnect_vpn(force=True)
    print_json(disconnect_result)
    
    # Step 9: Verify disconnection
    print_section("9. Verifying Disconnection")
    time.sleep(2)
    final_status = get_wireguard_status()
    
    if not final_status.get('connected'):
        print("✅ Successfully disconnected")
    else:
        print("⚠️  Still shows connected:")
        print_json(final_status)
    
    # Check IP after disconnect
    final_ip = get_current_connection_info()
    if final_ip.get('success'):
        print(f"\nCurrent IP: {final_ip['current_ip']} ({final_ip['country']})")
        
        if before_ip.get('success') and final_ip['current_ip'] == before_ip['current_ip']:
            print("✅ Back to original IP!")
    
    # Final summary
    print_section("✅ TEST COMPLETE - SUMMARY")
    print(f"  Account:          {MULLVAD_ACCOUNT[:4]}****{MULLVAD_ACCOUNT[-4:]}")
    print(f"  Server:           {server_id}")
    print(f"  Before IP:        {before_ip.get('current_ip', 'N/A')} ({before_ip.get('country', 'N/A')})")
    print(f"  VPN IP:           {after_ip.get('current_ip', 'N/A')} ({after_ip.get('country', 'N/A')})")
    print(f"  After Disconnect: {final_ip.get('current_ip', 'N/A')} ({final_ip.get('country', 'N/A')})")
    
    if before_ip.get('success') and after_ip.get('success'):
        ip_changed = before_ip['current_ip'] != after_ip['current_ip']
        print(f"  IP Changed:       {'Yes ✅' if ip_changed else 'No ⚠️'}")
    
    if test_result.get('internet_working'):
        print(f"  Internet Worked:  Yes ✅")
    else:
        print(f"  Internet Worked:  Unknown/No ⚠️")
    
    if result.get('connection', {}).get('authenticated'):
        print(f"  Authenticated:    Yes ✅")
    else:
        print(f"  Authenticated:    No ⚠️")


if __name__ == "__main__":
    try:
        authenticated_vpn_test()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted! Disconnecting...")
        disconnect_vpn(force=True)
        print("✅ Disconnected safely")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n⚠️  Attempting to disconnect...")
        disconnect_vpn(force=True)
