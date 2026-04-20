"""
Real VPN API Integration Examples
==================================

This file demonstrates actual VPN APIs you can integrate into your tools.py
"""

import requests
import json
import socket
import subprocess
from typing import Dict, List, Optional

# =============================================================================
# 1. MULLVAD VPN API (Public, no authentication required)
# =============================================================================

def get_mullvad_servers(country_code: Optional[str] = None) -> List[Dict]:
    """
    Get server list from Mullvad VPN's public API
    
    Args:
        country_code: Filter by country (e.g., 'us', 'se', 'de')
    
    Returns:
        List of VPN servers with full details
    """
    try:
        response = requests.get('https://api.mullvad.net/www/relays/all/', timeout=10)
        servers = response.json()
        
        # Filter WireGuard servers
        wg_servers = [s for s in servers if s.get('type') == 'wireguard' and s.get('active')]
        
        # Filter by country if specified
        if country_code:
            wg_servers = [s for s in wg_servers if s.get('country_code') == country_code.lower()]
        
        # Format the data
        formatted_servers = []
        for server in wg_servers[:10]:  # Limit to 10 for display
            formatted_servers.append({
                'hostname': server.get('hostname'),
                'country': server.get('country_name'),
                'city': server.get('city_name'),
                'ipv4': server.get('ipv4_addr_in'),
                'ipv6': server.get('ipv6_addr_in'),
                'pubkey': server.get('pubkey'),
                'load': f"{server.get('load', 'N/A')}",
                'port': server.get('multihop_port', 51820),
                'provider': server.get('provider'),
                'owned': server.get('owned', False)
            })
        
        return formatted_servers
    
    except Exception as e:
        print(f"Error fetching Mullvad servers: {e}")
        return []


# =============================================================================
# 2. OPENVPN MANAGEMENT INTERFACE
# =============================================================================

class OpenVPNManagement:
    """
    Interface for OpenVPN Management Protocol
    Connects via TCP socket to manage running OpenVPN instance
    """
    
    def __init__(self, host='127.0.0.1', port=7505):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        """Connect to OpenVPN management interface"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            # Read welcome message
            self.socket.recv(4096)
            return True
        except Exception as e:
            print(f"Failed to connect to OpenVPN: {e}")
            return False
    
    def send_command(self, command: str) -> str:
        """Send command to OpenVPN and get response"""
        if not self.socket:
            return "Not connected"
        
        try:
            self.socket.send(f"{command}\n".encode())
            response = self.socket.recv(4096).decode()
            return response
        except Exception as e:
            return f"Error: {e}"
    
    def get_state(self) -> Dict:
        """Get current VPN connection state"""
        response = self.send_command("state")
        # Parse response: timestamp,state,description,local_ip,remote_ip
        return {'raw': response}
    
    def get_status(self) -> Dict:
        """Get detailed connection status"""
        response = self.send_command("status")
        return {'raw': response}
    
    def get_bytecount(self) -> Dict:
        """Get bandwidth statistics"""
        response = self.send_command("bytecount 1")
        return {'raw': response}
    
    def disconnect(self):
        """Disconnect from management interface"""
        if self.socket:
            self.socket.close()


# =============================================================================
# 3. WIREGUARD INTERFACE (via wg command)
# =============================================================================

def get_wireguard_status() -> Dict:
    """
    Get WireGuard connection status using 'wg show' command
    Requires WireGuard to be installed on the system
    """
    try:
        result = subprocess.run(
            ['wg', 'show'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return {
                'success': True,
                'output': result.stdout,
                'interfaces': parse_wg_output(result.stdout)
            }
        else:
            return {
                'success': False,
                'error': result.stderr
            }
    except FileNotFoundError:
        return {
            'success': False,
            'error': 'WireGuard not installed. Install with: sudo apt install wireguard-tools'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def parse_wg_output(output: str) -> List[Dict]:
    """Parse wg show output into structured data"""
    interfaces = []
    current_interface = None
    
    for line in output.split('\n'):
        line = line.strip()
        if line.startswith('interface:'):
            if current_interface:
                interfaces.append(current_interface)
            current_interface = {'name': line.split(':')[1].strip(), 'peers': []}
        elif line.startswith('public key:') and current_interface:
            current_interface['public_key'] = line.split(':')[1].strip()
        elif line.startswith('listening port:') and current_interface:
            current_interface['port'] = line.split(':')[1].strip()
    
    if current_interface:
        interfaces.append(current_interface)
    
    return interfaces


# =============================================================================
# 4. PROTONVPN API (Location check)
# =============================================================================

def get_current_location() -> Dict:
    """
    Get current IP location (useful to verify VPN is working)
    Uses ProtonVPN's public API
    """
    try:
        response = requests.get('https://api.protonvpn.ch/vpn/location', timeout=10)
        data = response.json()
        
        return {
            'success': True,
            'ip': data.get('IP'),
            'country': data.get('Country'),
            'isp': data.get('ISP'),
            'latitude': data.get('Lat'),
            'longitude': data.get('Long')
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# =============================================================================
# 5. NORDVPN API ALTERNATIVES (Third-party endpoints)
# =============================================================================

def get_recommended_server(country: str = 'US') -> Dict:
    """
    Alternative: Use VPN Gate (free academic VPN) API
    Public VPN servers database
    """
    try:
        # VPN Gate provides CSV data
        response = requests.get('http://www.vpngate.net/api/iphone/', timeout=10)
        
        # Parse CSV (skip first line, it's metadata)
        lines = response.text.split('\n')
        if len(lines) > 2:
            headers = lines[1].split(',')
            
            servers = []
            for line in lines[2:10]:  # Get first 10 servers
                if line.strip():
                    values = line.split(',')
                    if len(values) >= len(headers):
                        server = dict(zip(headers, values))
                        if server.get('CountryShort') == country:
                            servers.append({
                                'hostname': server.get('HostName'),
                                'ip': server.get('IP'),
                                'country': server.get('CountryLong'),
                                'speed': server.get('Speed'),
                                'protocol': 'OpenVPN'
                            })
            
            return {
                'success': True,
                'servers': servers
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("VPN API Examples - Real World Data")
    print("=" * 70)
    
    # 1. Mullvad Servers
    print("\n1. MULLVAD VPN SERVERS (POLAND)")
    print("-" * 70)
    pl_servers = get_mullvad_servers('pl')
    for server in pl_servers[:3]:
        print(f"  {server['hostname']}: {server['city']}, {server['country']}")
        print(f"    IP: {server['ipv4']}")
        print(f"    Provider: {server['provider']}, Owned: {server['owned']}")
        print()
    
    # 2. Current Location (IP check)
    print("\n2. CURRENT IP LOCATION")
    print("-" * 70)
    location = get_current_location()
    if location['success']:
        print(f"  IP: {location['ip']}")
        print(f"  Country: {location['country']}")
        print(f"  ISP: {location['isp']}")
        print()
    
    # 3. WireGuard Status
    print("\n3. WIREGUARD STATUS")
    print("-" * 70)
    wg_status = get_wireguard_status()
    if wg_status['success']:
        print(f"  {wg_status['output']}")
    else:
        print(f"  {wg_status['error']}")
    
    print("\n" + "=" * 70)
    print("Integration Instructions:")
    print("=" * 70)
    print("""
1. Install dependencies:
   pip install requests

2. For WireGuard (optional):
   - Linux: sudo apt install wireguard-tools
   - Windows: Download from https://www.wireguard.com/install/
   - Mac: brew install wireguard-tools

3. For OpenVPN Management (optional):
   - Start OpenVPN with: --management localhost 7505
   
4. Use these functions in your tools.py file to provide real VPN data!
    """)
