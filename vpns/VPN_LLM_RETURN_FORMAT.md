# VPN LLM Return Format

## Overview

The `llm_vpn_execution.run()` function now returns a comprehensive dictionary with all execution details for the "head" LLM to process.

---

## Return Structure

```python
{
    "success": bool,              # Overall execution success (True/False)
    "vpn_connected": bool,        # Was VPN successfully connected?
    "vpn_disconnected": bool,     # Was VPN successfully disconnected?
    "connection_info": dict|None, # VPN connection details (if connected)
    "disconnect_info": dict|None, # VPN disconnection details (if disconnected)
    "final_response": str|None,   # Final LLM response text
    "tools_executed": list,       # List of all tools that were called
    "error": str|None,            # Error message (if execution failed)
    "iterations": int             # Number of loop iterations used
}
```

---

## Field Descriptions

### `success` (bool)
- `True`: Execution completed successfully
- `False`: Execution failed with an error

### `vpn_connected` (bool)
- `True`: VPN connection was established
- `False`: No VPN connection was made

### `vpn_disconnected` (bool)
- `True`: VPN was disconnected
- `False`: No VPN disconnection occurred

### `connection_info` (dict | None)
Present when `vpn_connected == True`:
```python
{
    "server_id": "fr-par-wg-001",
    "server_name": "Paris, France",
    "protocol": "wireguard",
    "status": "connected",
    "server_ip": "193.32.126.66",
    "config_path": "C:\\Users\\...\\fr-par-wg-001.conf",
    "provider": "31173",
    "tunnel_name": "fr-par-wg-001",
    "test_mode": False,
    "authenticated": True,
    "mode": "PRODUCTION MODE: Authenticated with Mullvad. All traffic routed through VPN with working internet!",
    "authentication": "✅ WireGuard key registered with Mullvad API - Internet will work!",
    "warning": None
}
```

### `disconnect_info` (dict | None)
Present when `vpn_disconnected == True`:
```python
{
    "tunnel_name": "fr-par-wg-001",
    "status": "disconnected",
    "force": True,
    "tunnel_removed": True
}
```

### `final_response` (str | None)
The final text response from the VPN LLM after all tools executed.

Example:
```
"I've successfully connected to the VPN server in Paris, France. 
The connection is authenticated with Mullvad and all traffic is now 
routed through the VPN tunnel."
```

### `tools_executed` (list)
List of all tools that were called during execution:
```python
[
    {
        "name": "list_vpn_servers",
        "args": {"region": "eu-west"},
        "success": True,
        "execution_time": 0.523
    },
    {
        "name": "connect_to_vpn",
        "args": {
            "server_id": "fr-par-wg-001",
            "mullvad_account": "9178****3875"
        },
        "success": True,
        "execution_time": 2.145
    }
]
```

### `error` (str | None)
Error message if execution failed:
```python
"Error code: 400 - {'error': {'message': '...'}}"
```

### `iterations` (int)
Number of loop iterations the execution took (usually 1-2).

---

## Usage Examples

### Example 1: Connection Scenario

**User asks**: "Connect to a VPN server in Europe"

**Return value**:
```python
{
    "success": True,
    "vpn_connected": True,
    "vpn_disconnected": False,
    "connection_info": {
        "server_name": "Paris, France",
        "tunnel_name": "fr-par-wg-001",
        "authenticated": True,
        "mode": "PRODUCTION MODE..."
    },
    "disconnect_info": None,
    "final_response": "Connected to Paris VPN server successfully.",
    "tools_executed": [
        {"name": "list_vpn_servers", "success": True},
        {"name": "connect_to_vpn", "success": True}
    ],
    "error": None,
    "iterations": 1
}
```

### Example 2: Disconnection Scenario

**User asks**: "Disconnect from VPN"

**Return value**:
```python
{
    "success": True,
    "vpn_connected": False,
    "vpn_disconnected": True,
    "connection_info": None,
    "disconnect_info": {
        "tunnel_name": "fr-par-wg-001",
        "status": "disconnected",
        "tunnel_removed": True
    },
    "final_response": "VPN disconnected successfully.",
    "tools_executed": [
        {"name": "disconnect_vpn", "success": True}
    ],
    "error": None,
    "iterations": 1
}
```

### Example 3: Full Workflow Scenario

**User asks**: "List servers, connect to one, check status, then disconnect"

**Return value**:
```python
{
    "success": True,
    "vpn_connected": True,
    "vpn_disconnected": False,  # Breaks on first connect
    "connection_info": {...},
    "disconnect_info": None,
    "final_response": "Connected to VPN server.",
    "tools_executed": [
        {"name": "list_vpn_servers", "success": True},
        {"name": "connect_to_vpn", "success": True},
        # Loop breaks here!
    ],
    "error": None,
    "iterations": 1
}
```

### Example 4: Error Scenario

**User asks**: "Connect to invalid-server"

**Return value**:
```python
{
    "success": False,
    "vpn_connected": False,
    "vpn_disconnected": False,
    "connection_info": None,
    "disconnect_info": None,
    "final_response": None,
    "tools_executed": [],
    "error": "Server 'invalid-server' not found...",
    "iterations": 1
}
```

---

## Processing in Head LLM

```python
import llm_vpn_execution

# Execute VPN task
result = llm_vpn_execution.run(user_message)

# Process result
if result['success']:
    if result['vpn_connected']:
        # VPN was connected
        server = result['connection_info']['server_name']
        auth = result['connection_info']['authenticated']
        
        response = f"VPN connected to {server}. "
        if auth:
            response += "Fully authenticated with Mullvad API. Internet working!"
        
    elif result['vpn_disconnected']:
        # VPN was disconnected
        tunnel = result['disconnect_info']['tunnel_name']
        response = f"VPN disconnected from {tunnel}."
    
    else:
        # Other action (e.g., list servers)
        tools_used = [t['name'] for t in result['tools_executed']]
        response = f"VPN task completed. Tools used: {', '.join(tools_used)}"
    
    # Include LLM's response
    response += f"\n\nVPN Agent says: {result['final_response']}"
    
else:
    # Execution failed
    response = f"VPN task failed: {result['error']}"

print(response)
```

---

## Key Points for Head LLM

1. **Check `success` first** - determines if execution succeeded
2. **Check `vpn_connected` and `vpn_disconnected`** - determines what action was taken
3. **Use `connection_info` or `disconnect_info`** - get specific details
4. **Include `final_response`** - VPN LLM's natural language summary
5. **Check `tools_executed`** - see what operations were performed
6. **Handle `error`** - if `success == False`, explain the error

---

## Benefits

✅ **Complete information** - Head LLM knows exactly what happened  
✅ **VPN state tracking** - Connected/disconnected status  
✅ **Detailed context** - Server info, authentication status  
✅ **Tool visibility** - See what operations were performed  
✅ **Error handling** - Clear error messages  
✅ **Natural language** - LLM's own description included  

---

## Integration Example

```python
# In main.py (head LLM coordinator)

import llm_vpn_execution

def handle_vpn_request(user_message):
    """Head LLM delegates to VPN agent"""
    
    # Delegate to VPN agent
    vpn_result = llm_vpn_execution.run(user_message)
    
    # Build response for user based on result
    if vpn_result['success']:
        if vpn_result['vpn_connected']:
            return {
                "status": "vpn_active",
                "location": vpn_result['connection_info']['server_name'],
                "message": vpn_result['final_response']
            }
        elif vpn_result['vpn_disconnected']:
            return {
                "status": "vpn_inactive",
                "message": vpn_result['final_response']
            }
    else:
        return {
            "status": "error",
            "message": f"VPN error: {vpn_result['error']}"
        }
```

---

**See also**: `example_vpn_result_usage.py` for working code example
