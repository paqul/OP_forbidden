import os
import sys
import json
import subprocess
import requests
import tempfile
import base64
import time
from pathlib import Path
from typing import Dict, List, Optional

# WireGuard paths
WG_PATH = r"C:\Program Files\WireGuard\wg.exe"
WG_GUI_PATH = r"C:\Program Files\WireGuard\wireguard.exe"
WG_CONFIG_DIR = Path.home() / "AppData" / "Local" / "WireGuard" / "Configurations"
WG_KEYS_STORAGE = Path.home() / "AppData" / "Local" / "WireGuard" / "mullvad_keys.json"
LOGS_DIR = Path(__file__).parent / "logs"
SERVER_USAGE_FILE = Path(__file__).parent / "logs" / "server_usage.json"

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
                        "description": "Filter servers by geographic region. Options: 'us-east' or 'us-west' for USA, 'eu-west' for UK/Netherlands/France/Poland, 'eu-central' for Germany/Switzerland/Austria, 'asia-pacific' for Japan/Singapore/Australia/Hong Kong, 'africa' for South Africa/Nigeria/Kenya/Egypt, 'south-america' for Brazil/Argentina/Chile, 'middle-east' for UAE/Israel/Turkey, or ISO country code (e.g. 'de', 'nl', 'se'), or 'all' for worldwide (default: 'all')",
                        "enum": ["us-east", "us-west", "eu-west", "eu-central", "asia-pacific", "africa", "south-america", "middle-east", "all"]
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
            "description": "Get detailed information about a specific VPN server (IP, provider, network specs). NOTE: list_vpn_servers already returns status='online' for all results — do NOT call this for every server just to check if it's online. Only use this when you need the specific IPv4/IPv6 address or other details not provided by list_vpn_servers.",
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
            "description": "Connect to a Mullvad VPN server using WireGuard with authenticated access. Creates configuration file and activates tunnel. Use server_id from list_vpn_servers (e.g., 'us-nyc-wg-801'). ALWAYS provide mullvad_account parameter for production connection with working internet. Returns JSON with connection status and details. Requires WireGuard installed and admin privileges.",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "The hostname from list_vpn_servers (e.g., 'us-nyc-wg-801', 'se-got-wg-001')"
                    },
                    "mullvad_account": {
                        "type": "string",
                        "description": "Mullvad account number (16 digits) for authenticated connection. ALWAYS provide this for production VPN connection with working internet!"
                    },
                    "protocol": {
                        "type": "string",
                        "description": "VPN protocol to use (default: wireguard)",
                        "enum": ["wireguard", "openvpn", "auto"]
                    },
                    "test_mode": {
                        "type": "boolean",
                        "description": "DO NOT USE - For testing only. Always use false (default) for production connections."
                    }
                },
                "required": ["server_id", "mullvad_account"]
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
            "description": "Get current public IP, location, and VPN connection status. Returns your actual IP address, country, ISP, coordinates, AND if WireGuard VPN is connected (including which server). Use this to check if already connected to a specific server before reconnecting.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_server_usage_stats",
            "description": "Returns only servers that have been connected to before (parsed from log files), sorted by most-used first. Use this BEFORE list_vpn_servers to get the 'avoid list'. Any server NOT in this response has never been used — prefer those. Never-used servers are NOT listed to keep the response compact.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


def _load_stored_keys() -> Dict:
    """Load stored WireGuard keypairs from file."""
    try:
        if WG_KEYS_STORAGE.exists():
            with open(WG_KEYS_STORAGE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Warning: Could not load stored keys: {str(e)}")
        return {}


# ---------------------------------------------------------------------------
# VPN Usage Tracking — parsed from logs/*.log files
# ---------------------------------------------------------------------------

def get_server_usage_stats() -> Dict:
    """
    Return only servers that have been connected to at least once.
    Primary source: logs/server_usage.json (persistent, survives log rotation).
    Fallback: scan *.log files (covers connections made before this tracking was added).
    Merged result is sorted most-used first.
    Never-used servers are NOT listed — any server absent from this list is safe to use.
    """
    import re

    # --- Primary source: server_usage.json ---
    stats: Dict = {}  # server_id -> {count, last_used}
    if SERVER_USAGE_FILE.exists():
        try:
            with open(SERVER_USAGE_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            for sid, entry in raw.items():
                stats[sid] = {
                    'count': entry.get('count', 0),
                    'last_used': entry.get('last_used'),
                    'first_used': entry.get('first_used'),
                }
        except Exception:
            pass

    # --- Fallback: scan log files for connections not yet in the JSON ---
    _PATTERN = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
        r".*?Executing: connect_to_vpn\(\{.*?'server_id':\s*'([^']+)'"
    )
    if LOGS_DIR.exists():
        for log_file in sorted(LOGS_DIR.glob('*.log')):
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    for line in f:
                        m = _PATTERN.search(line)
                        if m:
                            ts, sid = m.group(1), m.group(2)
                            if sid not in stats:
                                # Only add entries NOT already captured in the JSON
                                stats[sid] = {'count': 0, 'last_used': None, 'first_used': None}
                                stats[sid]['count'] += 1
                                stats[sid]['last_used'] = ts
                                if stats[sid]['first_used'] is None:
                                    stats[sid]['first_used'] = ts
            except Exception:
                continue

    used = [
        {
            'server_id': sid,
            'connection_count': entry['count'],
            'last_used': entry['last_used'],
            'first_used': entry.get('first_used'),
        }
        for sid, entry in stats.items()
    ]
    used.sort(key=lambda r: -r['connection_count'])

    return {
        'success': True,
        'total_connections_recorded': sum(r['connection_count'] for r in used),
        'used_servers_count': len(used),
        'storage': str(SERVER_USAGE_FILE),
        'instruction': (
            'These servers have been used before. '
            'When choosing a server from list_vpn_servers, '
            'AVOID servers appearing in this list (especially those used recently or most often). '
            'Any server NOT listed here has never been used — prefer those.'
        ),
        'used_servers': used,
    }


def _save_stored_keys(keys_data: Dict):
    """Save WireGuard keypairs to file."""
    try:
        with open(WG_KEYS_STORAGE, 'w') as f:
            json.dump(keys_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save keys: {str(e)}")


def _get_or_create_keypair(account_number: str) -> tuple:
    """Get existing keypair for account or create new one if needed."""
    stored_keys = _load_stored_keys()
    
    # Check if we have a key for this account
    if account_number in stored_keys:
        key_data = stored_keys[account_number]
        private_key = key_data.get('private_key')
        public_key = key_data.get('public_key')
        
        if private_key and public_key:
            print(f"✅ Reusing existing WireGuard key for account {account_number[:4]}****{account_number[-4:]}")
            return private_key, public_key
    
    # Generate new keypair if none exists
    print(f"🔑 Generating new WireGuard keypair for account {account_number[:4]}****{account_number[-4:]}")
    private_key, public_key = _generate_wireguard_keypair()
    
    # Store the keypair
    stored_keys[account_number] = {
        'private_key': private_key,
        'public_key': public_key,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    _save_stored_keys(stored_keys)
    
    return private_key, public_key


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


def _register_key_with_mullvad(account_number: str, public_key: str) -> Dict:
    """Register WireGuard public key with Mullvad and get assigned IP addresses."""
    try:
        # Mullvad WireGuard API endpoint
        url = f"https://api.mullvad.net/wg/"
        
        # Send public key registration request (using form data, not JSON)
        response = requests.post(
            url,
            data={"account": account_number, "pubkey": public_key},
            timeout=10
        )
        
        # Accept both 200 and 201 as success (201 = Created)
        if response.status_code in [200, 201]:
            # Try parsing as JSON first
            try:
                data = response.json()
                ipv4 = data.get('ipv4_address')
                ipv6 = data.get('ipv6_address')
            except:
                # If not JSON, parse plain text response: "10.71.4.226/32,fc00:bbbb:bbbb:bb01::8:4e1/128"
                addresses = response.text.strip().split(',')
                ipv4 = addresses[0] if len(addresses) > 0 else None
                ipv6 = addresses[1] if len(addresses) > 1 else None
            
            return {
                "success": True,
                "ipv4_address": ipv4,
                "ipv6_address": ipv6,
                "pubkey": public_key
            }
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "Invalid Mullvad account number"
            }
        elif response.status_code == 403:
            return {
                "success": False,
                "error": "Account has no credit. Please add time at mullvad.net"
            }
        else:
            return {
                "success": False,
                "error": f"Mullvad API error: {response.status_code} - {response.text}"
            }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to contact Mullvad API: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Key registration failed: {str(e)}"
        }


def _create_wireguard_config(server_id: str, server_data: Dict, mullvad_account: str = None, test_mode: bool = False, assigned_ipv4: str = None, assigned_ipv6: str = None) -> str:
    """Create WireGuard configuration file for a Mullvad server."""
    try:
        # Get or create keypair for this connection
        # If using Mullvad account, reuse existing key to avoid hitting 5-key limit
        if mullvad_account and not test_mode:
            private_key, public_key = _get_or_create_keypair(mullvad_account)
        else:
            # For test mode, generate fresh keypair
            private_key, public_key = _generate_wireguard_keypair()
        
        # Extract server info
        server_ip = server_data['ipv4_addr_in']
        server_pubkey = server_data['pubkey']
        
        # If we have a Mullvad account, register the key and get assigned IPs
        if mullvad_account and not test_mode:
            registration = _register_key_with_mullvad(mullvad_account, public_key)
            
            if not registration.get('success'):
                raise Exception(f"Mullvad key registration failed: {registration.get('error')}")
            
            assigned_ipv4 = registration.get('ipv4_address')
            assigned_ipv6 = registration.get('ipv6_address')
        
        # Use assigned IPs if available, otherwise use generic IP
        if assigned_ipv4:
            # Mullvad API returns IPs with CIDR notation already included (e.g., "10.72.193.60/32")
            # So don't add /32 or /128 if it's already there
            ipv4_addr = assigned_ipv4 if '/' in assigned_ipv4 else f"{assigned_ipv4}/32"
            interface_addresses = ipv4_addr
            
            if assigned_ipv6:
                ipv6_addr = assigned_ipv6 if '/' in assigned_ipv6 else f"{assigned_ipv6}/128"
                interface_addresses += f", {ipv6_addr}"
        else:
            interface_addresses = "10.64.0.2/32"
        
        # In test mode, don't route all traffic (prevents internet loss)
        # In production mode, route all traffic through VPN
        if test_mode:
            allowed_ips = "10.64.0.0/10"
        else:
            allowed_ips = "0.0.0.0/0, ::/0"
        
        # Create WireGuard configuration
        config_content = f"""[Interface]
# WireGuard Configuration for {server_id}
PrivateKey = {private_key}
Address = {interface_addresses}
DNS = 193.138.218.74

[Peer]
PublicKey = {server_pubkey}
AllowedIPs = {allowed_ips}
Endpoint = {server_ip}:51820
"""
        
        if mullvad_account:
            account_comment = f"# Mullvad Account: {mullvad_account[:4]}****{mullvad_account[-4:]}\n"
            config_content = config_content.replace(
                f"# WireGuard Configuration for {server_id}",
                f"# WireGuard Configuration for {server_id}\n{account_comment}# Authenticated with Mullvad API"
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
        # Check for running WireGuard services
        result = subprocess.run(
            ["powershell", "-Command", 
             "Get-Service | Where-Object { $_.Name -like 'WireGuardTunnel$*' -and $_.Status -eq 'Running' } | Select-Object -ExpandProperty Name"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            return {
                "connected": False,
                "tunnel_name": None,
                "status": "disconnected"
            }
        
        # Parse service name to get tunnel name
        # Service name format: WireGuardTunnel$<tunnel_name>
        service_name = result.stdout.strip().split('\n')[0]
        if service_name.startswith("WireGuardTunnel$"):
            tunnel_name = service_name.replace("WireGuardTunnel$", "")
            return {
                "connected": True,
                "tunnel_name": tunnel_name,
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
    Returns JSON with server details (capped at 40 results to keep LLM context manageable)
    """
    try:
        response = requests.get('https://api.mullvad.net/www/relays/all/', timeout=10)
        all_servers = response.json()
        servers = [s for s in all_servers if s.get('type') == 'wireguard' and s.get('active')]

        # Named region aliases → list of country codes
        region_map = {
            "us-east": ["us"],
            "us-west": ["us"],
            "eu-west": ["gb", "nl", "fr", "pl"],
            "eu-central": ["de", "ch", "at"],
            "asia-pacific": ["jp", "sg", "au", "hk"],
            "africa": ["za", "ng", "ke", "eg"],
            "south-america": ["br", "ar", "cl", "co"],
            "middle-east": ["ae", "il", "tr"],
        }

        if region != "all":
            if region in region_map:
                # Named alias
                countries = region_map[region]
                servers = [s for s in servers if s.get('country_code') in countries]
            else:
                # Treat as a direct ISO country code (e.g. "de", "nl", "se", "us")
                servers = [s for s in servers if s.get('country_code') == region.lower()]

        # Cap at 40 servers — returning 500+ entries overwhelms the LLM context and
        # causes it to hallucinate server IDs instead of picking from the real list.
        servers = servers[:40]

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

        if not result_servers and region != "all":
            return {
                "success": False,
                "error": f"No servers found for region '{region}'. Try a different country code or region alias.",
                "available_aliases": list(region_map.keys()),
                "hint": "Use ISO country codes like 'de', 'nl', 'se', 'us', 'gb', or aliases above.",
                "servers": []
            }

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


def _record_server_usage(server_id: str) -> None:
    """Persist a connection attempt to server_usage.json (creates file if missing)."""
    import datetime
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data: Dict = {}
        if SERVER_USAGE_FILE.exists():
            try:
                with open(SERVER_USAGE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}
        entry = data.get(server_id, {'count': 0, 'last_used': None, 'first_used': None})
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry['count'] += 1
        entry['last_used'] = now
        if entry['first_used'] is None:
            entry['first_used'] = now
        data[server_id] = entry
        with open(SERVER_USAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass  # Never let tracking errors break the VPN connection


def connect_to_vpn(server_id: str, protocol: str = "wireguard", mullvad_account: str = None, test_mode: bool = False) -> Dict:
    """
    Connect to a Mullvad VPN server using WireGuard.
    Creates configuration file and activates tunnel.
    
    WARNING: Without mullvad_account, ALL INTERNET TRAFFIC will be routed through 
    an unauthenticated tunnel and WILL NOT WORK! You will lose internet access.
    
    Args:
        server_id: Server hostname from list_vpn_servers
        protocol: VPN protocol (wireguard recommended)
        mullvad_account: Your Mullvad account number (16 digits) - REQUIRED for internet!
        test_mode: If True, doesn't route all traffic (safe testing without account)
    
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
        
        # Warn about internet loss if no account provided
        if not mullvad_account and not test_mode:
            return {
                "success": False,
                "error": "INTERNET WILL BE LOST: Connecting without mullvad_account will route all traffic through unauthenticated tunnel!",
                "help": "Either provide 'mullvad_account' parameter OR use 'test_mode=True' to test safely",
                "mullvad_signup": "Get account at https://mullvad.net/en/account/create"
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
        
        # Create WireGuard configuration (with Mullvad API registration if account provided)
        try:
            config_path = _create_wireguard_config(server_id, server, mullvad_account, test_mode)
            registration_success = True
            registration_msg = "✅ Registered with Mullvad API" if mullvad_account and not test_mode else None
        except Exception as config_error:
            return {
                "success": False,
                "error": f"Configuration failed: {str(config_error)}",
                "help": "Check your Mullvad account number and internet connection"
            }
        
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
        
        # Start the tunnel using Windows Service
        tunnel_name = server_id
        service_name = f"WireGuardTunnel${tunnel_name}"
        
        # Start the service
        result = subprocess.run(
            ["powershell", "-Command", f"Start-Service -Name '{service_name}' -ErrorAction Stop"],
            capture_output=True,
            text=True,
            timeout=15
        )
        code = result.returncode
        
        # Check if service actually started
        if code != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            return {
                "success": False,
                "error": f"Failed to start WireGuard service: {error_msg}",
                "help": "Check Windows Event Viewer or run: Get-Service WireGuardTunnel$* | Format-List",
                "debug": {
                    "service_name": service_name,
                    "exit_code": code,
                    "stdout": result.stdout.strip(),
                    "stderr": error_msg
                }
            }
        
        # Determine connection mode and warnings
        if test_mode:
            mode_msg = "TEST MODE: Tunnel created without routing all traffic. Internet should still work."
            auth_msg = None
            warning = None
        elif mullvad_account:
            mode_msg = "PRODUCTION MODE: Authenticated with Mullvad. All traffic routed through VPN with working internet!"
            auth_msg = "✅ WireGuard key registered with Mullvad API - Internet will work!"
            warning = None
        else:
            mode_msg = "ERROR: This should not happen - mullvad_account check failed!"
            auth_msg = None
            warning = "CRITICAL: All traffic is routed through unauthenticated tunnel!"
        
        # Verify the service is actually running
        import time
        time.sleep(1)
        verify_status = get_wireguard_status()
        
        connection_info = {
            "server_id": server_id,
            "server_name": f"{server['city_name']}, {server['country_name']}",
            "protocol": "wireguard",
            "status": "connected" if verify_status.get('connected') else "started_but_not_connected",
            "server_ip": server['ipv4_addr_in'],
            "config_path": config_path,
            "provider": server.get('provider', 'Unknown'),
            "tunnel_name": tunnel_name,
            "test_mode": test_mode,
            "authenticated": mullvad_account is not None and not test_mode,
            "mode": mode_msg,
            "authentication": auth_msg,
            "warning": warning
        }

        # Record usage persistently so it survives log rotation
        _record_server_usage(server_id)

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
        service_name = f"WireGuardTunnel${tunnel_name}"
        
        # Stop the tunnel using Windows Service
        result = subprocess.run(
            ["powershell", "-Command", f"Stop-Service -Name '{service_name}' -Force"],
            capture_output=True,
            text=True,
            timeout=10
        )
        code = result.returncode
        
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
    Also includes WireGuard VPN connection status if connected.
    This shows your actual IP address and location (useful to verify VPN status).
    """
    try:
        # Get WireGuard connection status first
        wg_status = get_wireguard_status()
        
        # Call ProtonVPN's free location API
        response = requests.get('https://api.protonvpn.ch/vpn/location', timeout=10)
        location_data = response.json()
        
        result = {
            "success": True,
            "current_ip": location_data.get('IP'),
            "country": location_data.get('Country'),
            "isp": location_data.get('ISP'),
            "latitude": location_data.get('Lat'),
            "longitude": location_data.get('Long'),
            "vpn_connected": wg_status.get('connected', False),
            "vpn_server": wg_status.get('tunnel_name') if wg_status.get('connected') else None,
            "note": "This is your current public IP. VPN status shows if WireGuard tunnel is active."
        }
        
        return result
        
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


def test_vpn_connection() -> Dict:
    """
    Test if VPN connection is working by checking internet access.
    Use this after connecting to verify the tunnel has internet access.
    """
    try:
        # First check if a tunnel is running
        status = get_wireguard_status()
        
        if not status.get('connected'):
            return {
                "success": False,
                "error": "No active VPN connection to test",
                "help": "Connect to a VPN first using connect_to_vpn()"
            }
        
        # Try to access internet through the tunnel
        try:
            response = requests.get('https://api.protonvpn.ch/vpn/location', timeout=5)
            location_data = response.json()
            
            return {
                "success": True,
                "internet_working": True,
                "tunnel_name": status.get('tunnel_name'),
                "current_ip": location_data.get('IP'),
                "country": location_data.get('Country'),
                "isp": location_data.get('ISP'),
                "message": "VPN tunnel has working internet access!"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "internet_working": False,
                "tunnel_name": status.get('tunnel_name'),
                "error": "VPN tunnel is active but has NO INTERNET ACCESS",
                "reason": str(e),
                "help": "This happens without a valid Mullvad account. Disconnect with disconnect_vpn() to restore internet."
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Test failed: {str(e)}"
        }


def get_stored_keys_info() -> Dict:
    """
    Get information about stored WireGuard keys.
    Shows which accounts have keys stored and when they were created.
    """
    try:
        stored_keys = _load_stored_keys()
        
        if not stored_keys:
            return {
                "success": True,
                "message": "No stored keys found",
                "keys_count": 0,
                "storage_file": str(WG_KEYS_STORAGE)
            }
        
        keys_info = []
        for account, key_data in stored_keys.items():
            keys_info.append({
                "account": f"{account[:4]}****{account[-4:]}",
                "public_key": key_data.get('public_key', 'N/A')[:20] + "...",
                "created_at": key_data.get('created_at', 'Unknown')
            })
        
        return {
            "success": True,
            "keys_count": len(stored_keys),
            "keys": keys_info,
            "storage_file": str(WG_KEYS_STORAGE),
            "note": "These keys are reused to avoid hitting Mullvad's 5-key limit"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get keys info: {str(e)}"
        }


def clear_stored_key(account_number: str) -> Dict:
    """
    Clear stored key for a specific Mullvad account.
    Next connection will generate a new key.
    """
    try:
        stored_keys = _load_stored_keys()
        
        if account_number not in stored_keys:
            return {
                "success": False,
                "error": f"No stored key found for account {account_number[:4]}****{account_number[-4:]}"
            }
        
        del stored_keys[account_number]
        _save_stored_keys(stored_keys)
        
        return {
            "success": True,
            "message": f"Cleared stored key for account {account_number[:4]}****{account_number[-4:]}",
            "remaining_keys": len(stored_keys)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to clear key: {str(e)}"
        }


def clear_all_stored_keys() -> Dict:
    """
    Clear all stored WireGuard keys.
    Next connections will generate new keys.
    """
    try:
        stored_keys = _load_stored_keys()
        count = len(stored_keys)
        
        _save_stored_keys({})
        
        return {
            "success": True,
            "message": f"Cleared {count} stored key(s)",
            "storage_file": str(WG_KEYS_STORAGE)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to clear keys: {str(e)}"
        }
