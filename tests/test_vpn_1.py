import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpn_tools import (
    list_vpn_servers, 
    get_vpn_server_status, 
    connect_to_vpn, 
    disconnect_vpn, 
    get_current_connection_info,
    get_wireguard_status,
    list_configured_tunnels,
    check_wireguard_installation
)


def print_json(data, title=""):
    """Pretty print JSON data."""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print('='*60)
    print(json.dumps(data, indent=2))
    print()


def test_wireguard_installation():
    """Test 1: Check if WireGuard is properly installed."""
    status = check_wireguard_installation()
    print_json(status, "Test 1: WireGuard Installation Status")
    
    # Show admin warning if not running as admin
    if not status.get('running_as_admin'):
        print("⚠️  WARNING: Not running as Administrator!")
        print("   Connection/disconnection tests will FAIL without admin rights.")
        print("   To fix: Right-click Python/VS Code → 'Run as Administrator'\n")
    else:
        print("✅ Running with Administrator privileges - Full functionality available\n")


def test_list_vpn_servers():
    """Test 2: List available VPN servers."""
    servers = list_vpn_servers(region="all")  # Get European servers
    print_json(servers, f"Test 2: Available VPN Servers (Found {servers.get('count', 0)})")
    return servers


def test_server_status(server_id):
    """Test 3: Get detailed status of a specific server."""
    status = get_vpn_server_status(server_id)
    print_json(status, f"Test 3: Server Status for {server_id}")
    return status


def test_current_ip():
    """Test 4: Check current IP address and location."""
    ip_info = get_current_connection_info()
    print_json(ip_info, "Test 4: Current IP Information")
    return ip_info


def test_wireguard_status():
    """Test 5: Check WireGuard connection status."""
    status = get_wireguard_status()
    print_json(status, "Test 5: WireGuard Connection Status")
    return status


def test_configured_tunnels():
    """Test 6: List all configured tunnels."""
    tunnels = list_configured_tunnels()
    print_json(tunnels, "Test 6: Configured WireGuard Tunnels")
    return tunnels


def test_connect_disconnect(server_id):
    """Test 7 & 8: Connect to VPN and then disconnect."""
    print("\n" + "="*60)
    print("  Test 7: Connecting to VPN (Creating config only)")
    print("="*60)
    print(f"NOTE: Connecting to {server_id}")
    print("This will create a WireGuard config but may not fully connect")
    print("without a Mullvad account number.\n")
    
    # Connect
    connect_result = connect_to_vpn(server_id)
    print_json(connect_result, "")

    print_json(get_current_connection_info(), "Current IP Information After Connection")  # Show IP info after connection attempt

    if connect_result.get('success'):
        # Check status after connection
        import time
        time.sleep(2)
        status = get_wireguard_status()
        print_json(status, "Connection Status Check")
        
        # Disconnect
        print_json(disconnect_vpn(force=True), "Test 8: Disconnecting from VPN")
    
    return connect_result


def run_all_tests():
    """Run comprehensive VPN tool tests."""
    print("\n" + "🔧 "*20)
    print("  WIREGUARD VPN TOOLS - COMPREHENSIVE TEST SUITE")
    print("🔧 "*20)
    
    # Test 1: Installation check
    test_wireguard_installation()
    
    # Test 2: List servers
    servers = test_list_vpn_servers()
    
    if not servers.get('success') or servers.get('count', 0) == 0:
        print("❌ Could not fetch servers. Stopping tests.")
        return
    
    # Pick first available server
    first_server = servers['servers'][0]
    server_id = first_server['server_id']
    
    # Test 3: Server status
    test_server_status(server_id)
    
    # Test 4: Current IP
    test_current_ip()
    
    # Test 5: WireGuard status
    test_wireguard_status()
    
    # Test 6: Configured tunnels
    test_configured_tunnels()
    
    # Test 7 & 8: Connect/Disconnect (optional - commented for safety)
    print("\n" + "⚠️ "*20)
    print("  CONNECTION TEST AVAILABLE")
    print("⚠️ "*20)
    print(f"\nTo test actual VPN connection, uncomment the line below.")
    print(f"Server to test: {server_id} ({first_server['name']})")
    print("\nNote: Full connection requires a Mullvad account number.")
    print("Without it, config will be created but authentication may fail.\n")
    
    # Uncomment to test actual connection:
    test_connect_disconnect(server_id)
    
    print("\n" + "✅ "*20)
    print("  TESTS COMPLETED")
    print("✅ "*20 + "\n")


if __name__ == "__main__":
    run_all_tests()
