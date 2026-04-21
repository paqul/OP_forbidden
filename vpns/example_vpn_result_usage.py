"""
Example: Using VPN LLM Execution Results
=========================================

This shows how the "head" LLM can use the information returned by llm_vpn_execution.run()
"""

import llm_vpn_execution

# Call the VPN LLM agent
result = llm_vpn_execution.run()

# Result structure example:
"""
{
    "success": True,                    # Overall execution success
    "vpn_connected": True,              # Was VPN connected?
    "vpn_disconnected": False,          # Was VPN disconnected?
    "connection_info": {                # Details if connected
        "server_id": "fr-par-wg-001",
        "server_name": "Paris, France",
        "tunnel_name": "fr-par-wg-001",
        "authenticated": True,
        "test_mode": False,
        "mode": "PRODUCTION MODE: Authenticated with Mullvad...",
        "authentication": "✅ WireGuard key registered with Mullvad API..."
    },
    "disconnect_info": None,            # Details if disconnected
    "final_response": "I've successfully...",  # LLM's final response
    "tools_executed": [                 # List of all tools called
        {
            "name": "list_vpn_servers",
            "args": {"region": "eu-west"},
            "success": True,
            "execution_time": 0.523
        },
        {
            "name": "connect_to_vpn",
            "args": {"server_id": "fr-par-wg-001", "mullvad_account": "..."},
            "success": True,
            "execution_time": 2.145
        }
    ],
    "error": None,                      # Error message if failed
    "iterations": 1                     # Number of loop iterations
}
"""

# How the head LLM can use this information:

def process_vpn_result(result):
    """Process VPN execution result for head LLM"""
    
    if not result['success']:
        return f"VPN task failed: {result['error']}"
    
    # Check what happened
    if result['vpn_connected']:
        conn = result['connection_info']
        return {
            "status": "vpn_connected",
            "server": conn.get('server_name'),
            "tunnel": conn.get('tunnel_name'),
            "authenticated": conn.get('authenticated'),
            "message": f"VPN connected to {conn.get('server_name')} successfully",
            "llm_response": result['final_response']
        }
    
    elif result['vpn_disconnected']:
        disc = result['disconnect_info']
        return {
            "status": "vpn_disconnected",
            "tunnel": disc.get('tunnel_name'),
            "message": f"VPN disconnected from {disc.get('tunnel_name')} successfully",
            "llm_response": result['final_response']
        }
    
    else:
        return {
            "status": "no_vpn_action",
            "message": "VPN task completed but no connection/disconnection occurred",
            "tools_used": [tool['name'] for tool in result['tools_executed']],
            "llm_response": result['final_response']
        }


# Example usage:
if __name__ == "__main__":
    result = llm_vpn_execution.run()
    
    print("\n" + "="*70)
    print("VPN EXECUTION RESULT FOR HEAD LLM")
    print("="*70)
    
    processed = process_vpn_result(result)
    
    if isinstance(processed, dict):
        print(f"\nStatus: {processed['status']}")
        print(f"Message: {processed['message']}")
        
        if 'server' in processed:
            print(f"Server: {processed['server']}")
            print(f"Authenticated: {processed['authenticated']}")
        
        print(f"\nLLM Response: {processed['llm_response']}")
        
        print(f"\nTools executed: {len(result['tools_executed'])}")
        for tool in result['tools_executed']:
            print(f"  - {tool['name']} ({tool['execution_time']:.2f}s)")
    else:
        print(f"\n{processed}")
    
    print("\n" + "="*70)
