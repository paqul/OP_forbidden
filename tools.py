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
            "description": "List all available VPN servers with their status, location, and connection details. Returns a structured list of VPN servers from the MCP context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Filter VPN servers by region (e.g., 'us-east', 'eu-west', 'asia'). Leave empty for all regions.",
                        "enum": ["us-east", "us-west", "eu-west", "eu-central", "asia-pacific", "all"]
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by server status",
                        "enum": ["online", "offline", "maintenance", "all"]
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
            "description": "Get detailed status information about a specific VPN server including latency, load, bandwidth, and connection count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "The unique identifier of the VPN server (e.g., 'vpn-us-east-01')"
                    },
                    "include_metrics": {
                        "type": "boolean",
                        "description": "Include detailed performance metrics (latency, bandwidth, load)"
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
            "description": "Establish a connection to a VPN server. This function initiates the connection process and returns the connection status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "The unique identifier of the VPN server to connect to"
                    },
                    "protocol": {
                        "type": "string",
                        "description": "VPN protocol to use",
                        "enum": ["openvpn", "wireguard", "ikev2", "auto"]
                    },
                    "credentials": {
                        "type": "object",
                        "description": "Authentication credentials (username/password or certificate)",
                        "properties": {
                            "username": {"type": "string"},
                            "password": {"type": "string"}
                        }
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
            "description": "Disconnect from the currently active VPN connection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Force disconnect even if active transfers are in progress"
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
            "description": "Get information about the current VPN connection including IP address, location, bandwidth usage, and connection duration.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


def list_vpn_servers(region: str = "all", status: str = "all") -> Dict:
    """
    Get REAL VPN servers from Mullvad API (free, no auth required)
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
                "load": "Unknown",  # API doesn't provide load
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


def get_vpn_server_status(server_id: str, include_metrics: bool = True) -> Dict:
    """
    Get detailed status for a specific VPN server.
    """
    # Mock implementation - replace with actual MCP server query
    server_data = {
        "server_id": server_id,
        "status": "online",
        "uptime": "45 days 12 hours",
        "location": "New York, USA",
        "ip_address": "203.0.113.45"
    }
    
    if include_metrics:
        server_data["metrics"] = {
            "latency": "12ms",
            "bandwidth_available": "10 Gbps",
            "bandwidth_used": "3.5 Gbps",
            "cpu_load": "35%",
            "memory_usage": "62%",
            "active_connections": 1247
        }
    
    return {
        "success": True,
        "data": server_data
    }


def connect_to_vpn(server_id: str, protocol: str = "auto", credentials: Optional[Dict] = None) -> Dict:
    """
    Connect to a VPN server.
    In production, this would use actual VPN client APIs or system commands.
    """
    try:
        # Mock connection - replace with actual VPN connection logic
        print(f"Initiating VPN connection to {server_id} using {protocol} protocol...")
        
        # Simulate connection process
        connection_info = {
            "server_id": server_id,
            "protocol": protocol,
            "status": "connected",
            "local_ip": "192.168.1.100",
            "vpn_ip": "10.8.0.6",
            "dns_servers": ["10.8.0.1", "10.8.0.2"],
            "connected_at": "2026-04-20T14:30:00Z"
        }
        
        return {
            "success": True,
            "message": f"Successfully connected to {server_id}",
            "connection": connection_info
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def disconnect_vpn(force: bool = False) -> Dict:
    """
    Disconnect from current VPN connection.
    """
    try:
        print(f"Disconnecting from VPN{'(forced)' if force else ''}...")
        
        return {
            "success": True,
            "message": "VPN disconnected successfully",
            "duration": "2 hours 34 minutes",
            "data_transferred": "1.2 GB"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_current_connection_info() -> Dict:
    """
    Get current VPN connection information.
    """
    is_connected = True
    
    if not is_connected:
        return {
            "success": True,
            "connected": False,
            "message": "No active VPN connection"
        }
    
    return {
        "success": True,
        "connected": True,
        "connection": {
            "server_id": "vpn-us-east-01",
            "server_name": "US East (New York)",
            "protocol": "wireguard",
            "local_ip": "192.168.1.100",
            "vpn_ip": "10.8.0.6",
            "public_ip": "203.0.113.45",
            "dns_servers": ["10.8.0.1", "10.8.0.2"],
            "connected_since": "2026-04-20T14:30:00Z",
            "duration": "2 hours 34 minutes",
            "data_sent": "342 MB",
            "data_received": "876 MB",
            "bandwidth": {
                "upload": "2.5 Mbps",
                "download": "8.3 Mbps"
            }
        }
    }

