import os
import sys
import json
import subprocess
import requests
import tempfile
import base64
from pathlib import Path
from typing import Dict, List, Optional

# WireGuard paths
WG_PATH = r"C:\Program Files\WireGuard\wg.exe"
WG_GUI_PATH = r"C:\Program Files\WireGuard\wireguard.exe"
WG_CONFIG_DIR = Path.home() / "AppData" / "Local" / "WireGuard" / "Configurations"

# Ensure config directory exists
WG_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


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
            "description": "Connect to a Mullvad VPN server using WireGuard. Creates configuration file and activates tunnel. Use server_id from list_vpn_servers (e.g., 'us-nyc-wg-801'). Returns JSON with connection status and details. Requires WireGuard installed.",
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
                    },
                    "mullvad_account": {
                        "type": "string",
                        "description": "Optional Mullvad account number for authenticated connection"
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
            "description": "Disconnect from active WireGuard VPN connection. Stops the tunnel and optionally removes it completely. Returns JSON with disconnect status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Force disconnect and remove tunnel service completely"
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


def _generate_wireguard_keypair() -> tuple:
    """Generate WireGuard private and public key pair."""
    try:
        # Generate private key
        result = subprocess.run(
            [WG_PATH, "genkey"],
            capture_output=True,
            text=True,
            check=True
        )
        private_key = result.stdout.strip()
        
        # Generate public key from private key
        result = subprocess.run(
            [WG_PATH, "pubkey"],
            input=private_key,
            capture_output=True,
            text=True,
            check=True
        )
        public_key = result.stdout.strip()
        
        return private_key, public_key
    except Exception as e:
        raise Exception(f"Failed to generate keypair: {str(e)}")


def _create_wireguard_config(server_id: str, server_data: Dict, mullvad_account: str = None) -> str:
    """Create WireGuard configuration file for a Mullvad server."""
    try:
        # Generate keypair for this connection
        private_key, public_key = _generate_wireguard_keypair()
        
        # Extract server info
        server_ip = server_data['ipv4_addr_in']
        server_pubkey = server_data['pubkey']
        
        # Note: For actual Mullvad connection, you need an account number
        # This creates a valid WireGuard config structure
        config_content = f"""[Interface]
# WireGuard Configuration for {server_id}
PrivateKey = {private_key}
Address = 10.64.0.2/32
DNS = 193.138.218.74

[Peer]
PublicKey = {server_pubkey}
AllowedIPs = 0.0.0.0/0
Endpoint = {server_ip}:51820
"""
        
        if mullvad_account:
            config_content = config_content.replace(
                f"PrivateKey = {private_key}",
                f"# Mullvad Account: {mullvad_account}\nPrivateKey = {private_key}"
            )
        
        # Save config file
        config_path = WG_CONFIG_DIR / f"{server_id}.conf"
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        return str(config_path)
    except Exception as e:
        raise Exception(f"Failed to create config: {str(e)}")


def _is_admin() -> bool:
    """Check if script is running with administrator privileges."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def _run_wireguard_cmd(args: List[str]) -> tuple:
    """Run WireGuard command and return output."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def get_wireguard_status() -> Dict:
    """Get current WireGuard connection status."""
    try:
        # Try to get tunnel status using wireguard.exe /tunnelstatus
        code, stdout, stderr = _run_wireguard_cmd([WG_GUI_PATH, "/tunnelstatus"])
        
        if code != 0:
            return {
                "connected": False,
                "tunnel_name": None,
                "status": "disconnected"
            }
        
        # Parse output to get active tunnel
        lines = stdout.strip().split('\n')
        active_tunnel = None
        for line in lines:
            if line.strip():
                active_tunnel = line.strip()
                break
        
        if active_tunnel:
            return {
                "connected": True,
                "tunnel_name": active_tunnel,
                "status": "connected"
            }
        else:
            return {
                "connected": False,
                "tunnel_name": None,
                "status": "disconnected"
            }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "status": "unknown"
        }


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


def connect_to_vpn(server_id: str, protocol: str = "wireguard", mullvad_account: str = None) -> Dict:
    """
    Connect to a Mullvad VPN server using WireGuard.
    Creates configuration file and activates tunnel.
    
    Note: For full Mullvad functionality, you need a Mullvad account number.
    Without it, the config is created but may not authenticate.
    
    REQUIRES: Administrator privileges on Windows
    """
    try:
        # Check for admin privileges
        if not _is_admin():
            return {
                "success": False,
                "error": "Administrator privileges required. Please run Python as Administrator.",
                "help": "Right-click Python/IDE and select 'Run as Administrator'"
            }
        
        # Check if already connected
        status = get_wireguard_status()
        if status.get('connected'):
            return {
                "success": False,
                "error": f"Already connected to tunnel: {status.get('tunnel_name')}. Disconnect first."
            }
        
        # Verify server exists in Mullvad network
        response = requests.get('https://api.mullvad.net/www/relays/all/', timeout=10)
        all_servers = response.json()
        server = next((s for s in all_servers if s.get('hostname') == server_id), None)
        
        if not server:
            return {
                "success": False,
                "error": f"Server '{server_id}' not found. Use list_vpn_servers to find valid servers."
            }
        
        # Create WireGuard configuration
        config_path = _create_wireguard_config(server_id, server, mullvad_account)
        
        # Activate tunnel using WireGuard GUI
        code, stdout, stderr = _run_wireguard_cmd([
            WG_GUI_PATH, 
            "/installtunnelservice", 
            config_path
        ])
        
        if code != 0 and "already exists" not in stderr.lower():
            return {
                "success": False,
                "error": f"Failed to install tunnel: {stderr}",
                "help": "Ensure WireGuard is installed and you have admin rights"
            }
        
        # Start the tunnel
        tunnel_name = server_id
        code, stdout, stderr = _run_wireguard_cmd([
            WG_GUI_PATH,
            "/start",
            tunnel_name
        ])
        
        connection_info = {
            "server_id": server_id,
            "server_name": f"{server['city_name']}, {server['country_name']}",
            "protocol": "wireguard",
            "status": "connected" if code == 0 else "connection_attempted",
            "server_ip": server['ipv4_addr_in'],
            "config_path": config_path,
            "provider": server.get('provider', 'Unknown'),
            "tunnel_name": tunnel_name,
            "note": "Config created. For full Mullvad access, add your account number." if not mullvad_account else "Connected with Mullvad account."
        }
        
        return {
            "success": True,
            "message": f"Connected to {server_id}",
            "connection": connection_info
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Connection failed: {str(e)}"
        }


def disconnect_vpn(force: bool = False) -> Dict:
    """
    Disconnect from active WireGuard VPN connection.
    Stops and optionally removes the tunnel.
    
    REQUIRES: Administrator privileges on Windows
    """
    try:
        # Check for admin privileges
        if not _is_admin():
            return {
                "success": False,
                "error": "Administrator privileges required. Please run Python as Administrator.",
                "help": "Right-click Python/IDE and select 'Run as Administrator'"
            }
        
        # Check current status
        status = get_wireguard_status()
        
        if not status.get('connected'):
            return {
                "success": True,
                "message": "No active VPN connection",
                "was_connected": False
            }
        
        tunnel_name = status.get('tunnel_name')
        
        # Stop the tunnel
        code, stdout, stderr = _run_wireguard_cmd([
            WG_GUI_PATH,
            "/stop",
            tunnel_name
        ])
        
        disconnect_info = {
            "tunnel_name": tunnel_name,
            "status": "disconnected" if code == 0 else "stop_attempted",
            "force": force
        }
        
        # Optionally remove tunnel service
        if force:
            code2, stdout2, stderr2 = _run_wireguard_cmd([
                WG_GUI_PATH,
                "/uninstalltunnelservice",
                tunnel_name
            ])
            disconnect_info["tunnel_removed"] = code2 == 0
        
        return {
            "success": code == 0,
            "message": f"Disconnected from {tunnel_name}" if code == 0 else "Disconnect attempted",
            "disconnect_info": disconnect_info
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Disconnect failed: {str(e)}"
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


def list_configured_tunnels() -> Dict:
    """List all WireGuard tunnels configured on this system."""
    try:
        configs = list(WG_CONFIG_DIR.glob("*.conf"))
        tunnels = []
        
        for config in configs:
            tunnel_name = config.stem
            tunnels.append({
                "name": tunnel_name,
                "config_path": str(config),
                "size": config.stat().st_size
            })
        
        return {
            "success": True,
            "count": len(tunnels),
            "tunnels": tunnels,
            "config_directory": str(WG_CONFIG_DIR)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def check_wireguard_installation() -> Dict:
    """Verify WireGuard is properly installed and accessible."""
    try:
        wg_exists = os.path.exists(WG_PATH)
        gui_exists = os.path.exists(WG_GUI_PATH)
        config_dir_exists = WG_CONFIG_DIR.exists()
        is_admin = _is_admin()
        
        # Try to get version
        version = None
        if wg_exists:
            try:
                result = subprocess.run(
                    [WG_PATH, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                version = result.stdout.strip() if result.returncode == 0 else None
            except:
                pass
        
        return {
            "success": wg_exists and gui_exists,
            "wg_cli_installed": wg_exists,
            "wg_gui_installed": gui_exists,
            "config_directory_exists": config_dir_exists,
            "running_as_admin": is_admin,
            "wg_path": WG_PATH,
            "gui_path": WG_GUI_PATH,
            "config_dir": str(WG_CONFIG_DIR),
            "version": version,
            "ready": wg_exists and gui_exists and config_dir_exists,
            "can_manage_tunnels": is_admin,
            "note": "Administrator privileges required for tunnel management" if not is_admin else "Running with admin privileges"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

