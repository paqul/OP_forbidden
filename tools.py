import os
import sys
import json
import subprocess
import requests
from typing import Dict, List, Optional


tools = [
    {
        "type": "function",
        "function": {
            "name": "list_vpn_servers",
            "description": "Get real-time list of available VPN servers from Mullvad network. Returns JSON with up to 10 active WireGuard servers including hostname, location (city/country), IP address, and provider. Each server in the response includes: server_id (hostname), name (city, country), region (country code), status (always 'online'), ip (IPv4 address), and provider name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Filter servers by geographic region. Options: 'us-east' or 'us-west' for USA, 'eu-west' for UK/Netherlands/Germany/France, 'eu-central' for Germany/Switzerland/Austria, 'asia-pacific' for Japan/Singapore/Australia/Hong Kong, or 'all' for worldwide servers (default: 'all')",
                        "enum": ["us-east", "us-west", "eu-west", "eu-central", "asia-pacific", "all"]
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vpn_server_status",
            "description": "Get detailed status information about a specific VPN server from Mullvad network. Use server_id from list_vpn_servers response (e.g., 'us-nyc-wg-801'). Returns JSON with server details, location, IP address, provider, and network specs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "The hostname of the VPN server (get this from list_vpn_servers, e.g., 'us-nyc-wg-801', 'se-got-wg-001')"
                    }
                },
                "required": ["server_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "connect_to_vpn",
            "description": "Simulate VPN connection to a Mullvad server. Use server_id from list_vpn_servers (e.g., 'us-nyc-wg-801'). Returns JSON with connection status, simulated IP addresses, and connection details. NOTE: This is a simulation - actual VPN connection requires WireGuard client installation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "The hostname from list_vpn_servers (e.g., 'us-nyc-wg-801', 'se-got-wg-001')"
                    },
                    "protocol": {
                        "type": "string",
                        "description": "VPN protocol to use (Mullvad uses WireGuard)",
                        "enum": ["wireguard", "openvpn", "auto"]
                    }
                },
                "required": ["server_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "disconnect_vpn",
            "description": "Simulate disconnecting from VPN connection. Returns JSON with success status and simulated connection duration/data transfer stats. NOTE: This is a simulation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Force disconnect (simulation parameter)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_connection_info",
            "description": "Get real current public IP location using ProtonVPN API. Returns JSON with your actual IP address, country, ISP, and geographic coordinates. Useful to verify if VPN would change your location.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


def list_vpn_servers(region: str = "all") -> Dict:
    """
    Get REAL VPN servers from Mullvad API (free, no auth required)
    Returns JSON with server details
    """
    try:
        response = requests.get('https://api.mullvad.net/www/relays/all/', timeout=10)
        all_servers = response.json()
        servers = [s for s in all_servers if s.get('type') == 'wireguard' and s.get('active')]
        region_map = {
            "us-east": ["us"],
            "us-west": ["us"],
            "eu-west": ["uk", "nl", "fr", "pl"],
            "eu-central": ["de", "ch", "at"],
            "asia-pacific": ["jp", "sg", "au", "hk"]
        }
        if region != "all" and region in region_map:
            countries = region_map[region]
            servers = [s for s in servers if s.get('country_code') in countries]
        result_servers = []
        for server in servers:
            result_servers.append({
                "server_id": server['hostname'],
                "name": f"{server['city_name']}, {server['country_name']}",
                "region": server['country_code'],
                "status": "online",
                "load": "Unknown",
                "latency": "Unknown",
                "ip": server['ipv4_addr_in'],
                "provider": server.get('provider', 'Unknown')
            })
        return {
            "success": True,
            "count": len(result_servers),
            "servers": result_servers
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not fetch servers: {str(e)}",
            "servers": []
        }


def get_vpn_server_status(server_id: str) -> Dict:
    """
    Get detailed status for a specific Mullvad VPN server.
    Fetches real-time data from Mullvad API for the specified server.
    """
    try:
        # Fetch all servers from Mullvad API
        response = requests.get('https://api.mullvad.net/www/relays/all/', timeout=10)
        all_servers = response.json()
        
        # Find the specific server by hostname
        server = next((s for s in all_servers if s.get('hostname') == server_id), None)
        
        if not server:
            return {
                "success": False,
                "error": f"Server '{server_id}' not found. Use list_vpn_servers to get valid server IDs."
            }
        
        # Format server details
        server_data = {
            "server_id": server['hostname'],
            "status": "online" if server.get('active') else "offline",
            "location": f"{server['city_name']}, {server['country_name']}",
            "country_code": server['country_code'],
            "ipv4_address": server['ipv4_addr_in'],
            "ipv6_address": server.get('ipv6_addr_in', 'N/A'),
            "provider": server.get('provider', 'Unknown'),
            "owned_by_mullvad": server.get('owned', False),
            "network_speed": f"{server.get('network_port_speed', 'Unknown')} Gbps",
            "wireguard_pubkey": server.get('pubkey', 'N/A')[:20] + "...",  # Truncate for display
            "type": server.get('type', 'Unknown')
        }
        
        return {
            "success": True,
            "data": server_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not fetch server status: {str(e)}"
        }


def connect_to_vpn(server_id: str, protocol: str = "wireguard") -> Dict:
    """
    Simulate VPN connection to a Mullvad server.
    In production, this would require WireGuard client and actual connection setup.
    """
    try:
        # Verify server exists in Mullvad network
        response = requests.get('https://api.mullvad.net/www/relays/all/', timeout=10)
        all_servers = response.json()
        server = next((s for s in all_servers if s.get('hostname') == server_id), None)
        
        if not server:
            return {
                "success": False,
                "error": f"Server '{server_id}' not found. Use list_vpn_servers to find valid servers."
            }
        
        # Simulate connection with real server data
        connection_info = {
            "server_id": server_id,
            "server_name": f"{server['city_name']}, {server['country_name']}",
            "protocol": protocol,
            "status": "connected (simulated)",
            "server_ip": server['ipv4_addr_in'],
            "simulated_vpn_ip": "10.8.0.6",
            "provider": server.get('provider', 'Unknown'),
            "connection_note": "This is a simulation. To actually connect, install WireGuard and use the server's public key.",
            "wireguard_port": server.get('multihop_port', 51820)
        }
        
        return {
            "success": True,
            "message": f"Simulated connection to {server_id}",
            "connection": connection_info
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def disconnect_vpn(force: bool = False) -> Dict:
    """
    Simulate disconnecting from VPN.
    In production, this would disconnect actual WireGuard/OpenVPN connection.
    """
    try:
        return {
            "success": True,
            "message": "VPN disconnected successfully (simulated)",
            "note": "This is a simulation. In production, would disconnect actual VPN client.",
            "simulated_stats": {
                "duration": "2 hours 34 minutes",
                "data_sent": "342 MB",
                "data_received": "876 MB",
                "total_transferred": "1.2 GB"
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_current_connection_info() -> Dict:
    """
    Get REAL current public IP and location using ProtonVPN API.
    This shows your actual IP address and location (useful to verify VPN status).
    """
    try:
        # Call ProtonVPN's free location API
        response = requests.get('https://api.protonvpn.ch/vpn/location', timeout=10)
        location_data = response.json()
        
        return {
            "success": True,
            "current_ip": location_data.get('IP'),
            "country": location_data.get('Country'),
            "isp": location_data.get('ISP'),
            "latitude": location_data.get('Lat'),
            "longitude": location_data.get('Long'),
            "note": "This is your REAL current IP. If connected to VPN, this would show VPN server's IP."
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not fetch location info: {str(e)}"
        }

