# VPN API Integration Guide

## Real VPN APIs & Data Sources

I've found several production-ready VPN APIs and protocols you can integrate into your MCP tools:

---

## 1. **Mullvad VPN Public API** ⭐ RECOMMENDED

**Endpoint:** `https://api.mullvad.net/www/relays/all/`

**Status:** ✅ **FREE, NO AUTHENTICATION REQUIRED**

### Features:
- Complete list of 1000+ VPN servers worldwide
- Real-time server status
- IPv4 and IPv6 addresses
- WireGuard public keys
- Server load statistics
- Provider information
- Location data (country, city)

### Example Response:
```json
{
  "hostname": "us-nyc-wg-801",
  "country_code": "us",
  "country_name": "USA",
  "city_name": "New York",
  "ipv4_addr_in": "23.234.100.3",
  "ipv6_addr_in": "2607:9000:a000:31::f001",
  "pubkey": "3XVRp858LSMwQ6pA2Zo5LFGf4nIjLnuTkbXTJiNPcUo=",
  "type": "wireguard",
  "active": true,
  "owned": false,
  "provider": "Tzulo",
  "network_port_speed": 10
}
```

### Python Integration:
```python
import requests

def get_mullvad_servers(country='us'):
    response = requests.get('https://api.mullvad.net/www/relays/all/')
    servers = response.json()
    wg_servers = [s for s in servers 
                  if s['type'] == 'wireguard' 
                  and s['active'] 
                  and s['country_code'] == country]
    return wg_servers
```

---

## 2. **OpenVPN Management Protocol**

**Connection:** TCP Socket (localhost:7505)

**Status:** ✅ **BUILT-IN TO OPENVPN**

### Features:
- Start/stop VPN connections
- Real-time connection state
- Bandwidth monitoring
- Client management (server mode)
- Password handling
- Connection statistics

### Available Commands:
```
state       - Get connection state (CONNECTING, CONNECTED, etc.)
status      - Get detailed connection status
bytecount   - Enable bandwidth monitoring
hold        - Hold connection initialization
signal      - Send signals (SIGHUP, SIGTERM, SIGUSR1, SIGUSR2)
kill        - Kill specific client (server mode)
```

### Example Usage:
```python
import socket

# Connect to OpenVPN management interface
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 7505))
sock.recv(4096)  # Read welcome message

# Get current state
sock.send(b"state\n")
response = sock.recv(4096).decode()
# Response: "1619000000,CONNECTED,SUCCESS,10.8.0.6,1.2.3.4"
```

### Setup:
Start OpenVPN with management enabled:
```bash
openvpn --config client.ovpn --management localhost 7505
```

---

## 3. **WireGuard CLI Interface**

**Command:** `wg show`

**Status:** ✅ **BUILT-IN TO WIREGUARD**

### Features:
- Interface information
- Peer status
- Handshake timing
- Transfer statistics
- Public/private key management

### Example Output:
```
interface: wg0
  public key: rWiQxq5lAWD8v/bws9ITSAvThyZW8cR2x+Ins9ZvvRo=
  private key: (hidden)
  listening port: 51820

peer: BLNHNoGO88LjV/wDBa7CUUwUzPq/fO2UwcGLy56hKy4=
  endpoint: 185.213.154.68:51820
  allowed ips: 0.0.0.0/0, ::/0
  latest handshake: 1 minute, 23 seconds ago
  transfer: 1.25 GiB received, 342 MiB sent
```

### Python Integration:
```python
import subprocess

def get_wireguard_status():
    result = subprocess.run(['wg', 'show'], 
                          capture_output=True, 
                          text=True)
    return result.stdout
```

---

## 4. **ProtonVPN Location API**

**Endpoint:** `https://api.protonvpn.ch/vpn/location`

**Status:** ✅ **FREE, PUBLIC**

### Features:
- Current IP address
- Geographic location
- ISP information
- Country code
- Coordinates

### Example Response:
```json
{
  "IP": "37.139.73.58",
  "Lat": 50.3571,
  "Long": 20.0386,
  "Country": "PL",
  "ISP": "Net Bis Sp Z O O",
  "Code": 1000
}
```

### Use Case:
Perfect for verifying VPN connection status by checking if IP/location changed.

---

## 5. **VPN Gate Academic Project**

**Endpoint:** `http://www.vpngate.net/api/iphone/`

**Status:** ✅ **FREE, NO AUTHENTICATION**

### Features:
- Free public VPN servers
- Global coverage
- OpenVPN configurations
- Real-time speed stats

### Format: CSV

Provides hundreds of free VPN servers operated by volunteers worldwide.

---

## Integration Strategy for Your Project

### Recommended Approach:

1. **Use Mullvad API for server discovery**
   - Get current VPN server list
   - Filter by region, load, speed
   - Return structured data to LLM

2. **Use OpenVPN Management for connection control**
   - Start/stop connections
   - Monitor bandwidth
   - Check connection status

3. **Use WireGuard for modern VPN protocol**
   - Fast, secure, modern
   - Simple configuration
   - Built-in status commands

4. **Use ProtonVPN API for IP verification**
   - Verify VPN is working
   - Check location change
   - Validate privacy

---

## Example LLM Function Tool Schema

```python
{
    "type": "function",
    "function": {
        "name": "get_vpn_servers",
        "description": "Get list of available VPN servers from Mullvad",
        "parameters": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "Country code (us, uk, de, se, etc.)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of servers to return"
                }
            }
        }
    }
}
```

---

## Security Considerations

1. **Never expose private keys** in LLM responses
2. **Validate all user inputs** before passing to VPN commands
3. **Use subprocess safely** - avoid shell injection
4. **Rate limit API calls** to public endpoints
5. **Handle credentials securely** - use environment variables

---

## Installation Requirements

```bash
# Python dependencies
pip install requests

# WireGuard (optional)
# Ubuntu/Debian:
sudo apt install wireguard-tools

# Windows:
# Download from https://www.wireguard.com/install/

# Mac:
brew install wireguard-tools

# OpenVPN (optional)
# Ubuntu/Debian:
sudo apt install openvpn

# Windows/Mac:
# Download from https://openvpn.net/community-downloads/
```

---

## Quick Start Examples

### Get US VPN Servers:
```python
import requests

servers = requests.get('https://api.mullvad.net/www/relays/all/').json()
us_servers = [s for s in servers if s['country_code'] == 'us' and s['active']]
print(f"Found {len(us_servers)} active US servers")
```

### Check Current IP:
```python
import requests

location = requests.get('https://api.protonvpn.ch/vpn/location').json()
print(f"Your IP: {location['IP']}")
print(f"Country: {location['Country']}")
```

### WireGuard Status:
```python
import subprocess

status = subprocess.run(['wg', 'show'], capture_output=True, text=True)
print(status.stdout)
```

---

## Additional Resources

- **Mullvad API Docs:** https://api.mullvad.net/
- **OpenVPN Management:** https://openvpn.net/community-resources/management-interface/
- **WireGuard Protocol:** https://www.wireguard.com/
- **VPN Gate Project:** https://www.vpngate.net/

---

## Next Steps

1. ✅ Test `vpn_api_examples.py` to verify APIs are working
2. ✅ Integrate desired functions into your `tools.py`
3. ✅ Add proper error handling and rate limiting
4. ✅ Update LLM prompts to understand VPN operations
5. ✅ Test with GPT to ensure function calling works correctly

**All APIs above are production-ready and can be used immediately!**
