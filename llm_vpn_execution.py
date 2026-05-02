from keys.projects_api_keys import open_ai_api_key, MULLVAD_ACCOUNT
from prompts.system_prompts import vpn_prompt
from openai import OpenAI
import builtins as _builtins
import logging as _logging
import json
import time
import urllib.request
import vpn_tools
from logger.logger_file import (log_user_request, log_gpt_request, log_gpt_response, log_tool_call_start,
    log_tool_call_result, log_final_response, log_error, log_session_summary,
    llm_logger as _file_logger)

_orig_print = _builtins.print

def _p(*args, sep=' ', end='\n', file=None, flush=False):
    _orig_print(*args, sep=sep, end=end, file=file, flush=flush)
    if file is None:
        msg = sep.join(str(a) for a in args)
        try:
            _file_logger._safe_log(_logging.DEBUG, msg)
        except Exception:
            pass

print = _p

llm_vpn_client = OpenAI(api_key=open_ai_api_key)


def _get_public_ip(timeout: int = 8) -> str | None:
    """Return the current public IP or None on failure."""
    try:
        req = urllib.request.Request(
            "https://api.ipify.org",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode().strip()
    except Exception:
        return None


def _verify_vpn_active(ip_before: str | None) -> dict:
    """
    Confirm that traffic is actually routed through the VPN by checking that
    the public IP changed after connecting.  Returns a result dict.

    Verification requires BOTH a known baseline AND a changed IP:
    - If ip_before was never captured (network was down before connecting),
      we cannot confirm anything → verified=False.
    - If ip_after cannot be fetched, the service is unreachable → verified=False.
    - If the IP did not change, traffic is not going through the VPN → verified=False.
    """
    if ip_before is None:
        return {
            "verified": False,
            "reason": "Baseline IP was not captured before connecting — cannot confirm VPN routing"
        }
    ip_after = _get_public_ip()
    if ip_after is None:
        return {"verified": False, "reason": "Could not reach IP-check service after connecting"}
    if ip_after == ip_before:
        return {
            "verified": False,
            "reason": f"Public IP did not change ({ip_after}) — traffic may not be routed through VPN",
            "ip": ip_after
        }
    return {"verified": True, "ip_before": ip_before, "ip_after": ip_after}

available_functions = {
    "list_vpn_servers": vpn_tools.list_vpn_servers,
    "get_vpn_server_status": vpn_tools.get_vpn_server_status,
    "connect_to_vpn": vpn_tools.connect_to_vpn,
    "disconnect_vpn": vpn_tools.disconnect_vpn,
    "get_current_connection_info": vpn_tools.get_current_connection_info,
}

# Configuration for tool guidance messages (data-driven approach)
TOOL_GUIDANCE = {
    "list_vpn_servers": {
        "on_success": lambda r: f"✅ Found {r.get('count', 0)} VPN servers available",
        "check_data": lambda r: r.get('count', 0) > 0
    },
    "get_vpn_server_status": {
        "on_success": lambda r: f"✅ Server {r['data']['server_id']} is {r['data']['status']} in {r['data']['location']}",
    },
    "connect_to_vpn": {
        "on_success": lambda r: _get_connection_guidance(r),
    },
    "get_current_connection_info": {
        "on_success": lambda r: f"✅ Location: {r.get('country', 'Unknown')}, IP: {r.get('current_ip', 'Unknown')}" + (f", Connected to VPN: {r.get('vpn_server', 'none')}" if r.get('vpn_connected') else ""),
    },
    "disconnect_vpn": {
        "on_success": lambda r: f"✅ Disconnected from {r.get('disconnect_info', {}).get('tunnel_name', 'Unknown')}",
    }
}


def _get_connection_guidance(response):
    """Generate guidance for connect_to_vpn based on connection status."""
    connection = response.get('connection', {})
    server_name = connection.get('server_name', 'Unknown')
    server_id = connection.get('server_id', 'Unknown')
    
    if connection.get('test_mode'):
        return f"⚠️ Connected to {server_name} in TEST MODE - should use mullvad_account for production!"
    elif connection.get('authenticated'):
        return f"✅ Successfully connected to {server_id} ({server_name}) with Mullvad authentication"
    else:
        return f"❌ Connected to {server_name} WITHOUT authentication. Will not work!"


def _generate_guidance_message(function_name, function_response):
    """Generate contextual guidance message for LLM based on tool execution."""
    if not function_response.get('success', True):
        error_msg = function_response.get('error', 'Unknown error')
        return f"❌ {function_name} failed: {error_msg}. Review and determine next action."
    
    tool_config = TOOL_GUIDANCE.get(function_name)
    if not tool_config:
        return ""
    
    # Check if there's a data validation function
    if 'check_data' in tool_config and not tool_config['check_data'](function_response):
        return ""
    
    # Generate success message
    return tool_config['on_success'](function_response)


def _print_status_banner(title, details=None):
    """Print a formatted status banner."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    if details:
        for key, value in details.items():
            print(f"   {key}: {value}")
    print(f"{'='*60}\n")


def _track_vpn_status(function_name, response, state):
    """Track VPN connection/disconnection status and print banners."""
    if function_name == "connect_to_vpn" and response.get('success'):
        state['vpn_connected'] = True
        connection_info = response.get('connection', {})
        state['connection_info'] = connection_info

        # Verify traffic is actually routed through VPN by checking public IP changed
        print("   🌐 Verifying VPN traffic routing via public IP check...")
        ip_check = _verify_vpn_active(state.get('_ip_before'))
        state['vpn_ip_verified'] = ip_check['verified']
        state['ip_check'] = ip_check
        if ip_check['verified']:
            print(f"   ✅ IP verified: {ip_check.get('ip_before')} → {ip_check.get('ip_after')}")
        else:
            print(f"   ⚠️  IP verification failed: {ip_check.get('reason')}")

        status = "Authenticated ✅" if connection_info.get('authenticated') else "Test mode"
        _print_status_banner("VPN CONNECTION ESTABLISHED!", {
            "Server": connection_info.get('server_name', 'Unknown'),
            "Tunnel": connection_info.get('tunnel_name', 'Unknown'),
            "Status": status,
            "IP Verified": "✅ Yes" if ip_check['verified'] else f"⚠️  No — {ip_check.get('reason', '')}"
        })
    
    elif function_name == "disconnect_vpn" and response.get('success'):
        state['vpn_disconnected'] = True
        disconnect_info = response.get('disconnect_info', {})
        state['disconnect_info'] = disconnect_info
        
        _print_status_banner("VPN DISCONNECTED SUCCESSFULLY!", {
            "Tunnel": disconnect_info.get('tunnel_name', 'Unknown'),
            "Status": disconnect_info.get('status', 'Unknown'),
            "Cleanup": "Complete ✅" if disconnect_info.get('tunnel_removed') else "Partial"
        })


def _execute_tool(tool_call, state):
    """Execute a single tool call and handle results."""
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)
    
    log_tool_call_start(function_name, function_args)
    print(f"Executing: {function_name}({function_args})")
    
    if function_name not in available_functions:
        error_msg = f"Function {function_name} not found"
        log_error(error_msg)
        print(f"ERROR: {error_msg}\n")
        return None
    
    try:
        start_time = time.time()
        response = available_functions[function_name](**function_args)
        execution_time = time.time() - start_time
        
        log_tool_call_result(function_name, response, execution_time)
        print(f"Result: {json.dumps(response, indent=2)}\n")
        
        # Track VPN status changes
        _track_vpn_status(function_name, response, state)
        
        # Track execution
        state['tools_executed'].append({
            "name": function_name,
            "args": function_args,
            "success": response.get('success', True),
            "execution_time": execution_time
        })
        
        # Generate guidance message
        guidance = _generate_guidance_message(function_name, response)
        
        return {
            "tool_call_id": tool_call.id,
            "response": response,
            "guidance": guidance
        }
        
    except Exception as e:
        log_error(f"Tool execution failed: {function_name}", e)
        print(f"ERROR executing {function_name}: {str(e)}\n")
        return None


def _is_workflow_complete(state):
    """Check if VPN workflow is complete."""
    # Require both successful connection AND that traffic is actually routed through VPN
    return state['vpn_connected'] and state.get('vpn_ip_verified', False)


def _build_result(state, success, iterations, final_response=None, error=None):
    """Build execution result dictionary."""
    return {
        "success": success,
        "vpn_connected": state['vpn_connected'],
        "vpn_ip_verified": state.get('vpn_ip_verified', False),
        "vpn_disconnected": state['vpn_disconnected'],
        "connection_info": state.get('connection_info'),
        "disconnect_info": state.get('disconnect_info'),
        "final_response": final_response,
        "tools_executed": state['tools_executed'],
        "error": error,
        "iterations": iterations
    }



def run(user_message: str = None):
    """Execute LLM-driven VPN workflow."""
    # Initialize state
    state = {
        'vpn_connected': False,
        'vpn_ip_verified': False,
        'vpn_disconnected': False,
        'connection_info': None,
        'disconnect_info': None,
        'tools_executed': [],
    }

    # Snapshot public IP before connecting so we can verify it changes
    ip_before = _get_public_ip()
    if ip_before:
        print(f"   🌐 Public IP before VPN: {ip_before}")
    state['_ip_before'] = ip_before
    
    # Setup initial message
    if not user_message:
        user_message = "Can you list all available VPN servers in any region and try connect to one of them? Also, check the connection info."
    
    log_user_request(user_message)
    
    # Build system prompt with credentials
    system_vpn_prompt = vpn_prompt + f"\n\nAVAILABLE CREDENTIALS:\n- Mullvad Account: {MULLVAD_ACCOUNT}\n\nALWAYS use this account when calling connect_to_vpn()."
    
    messages = [
        {"role": "system", "content": system_vpn_prompt},
        {"role": "user", "content": user_message}
    ]
    
    # Main execution loop
    model_name = "gpt-4o-mini"
    max_iterations = 10
    
    for iteration in range(max_iterations):
        try:
            # Call LLM
            print(f"\n{'='*60}")
            print(f"Iteration {iteration + 1} - Messages: {len(messages)}")
            print(f"{'='*60}\n")
            
            log_gpt_request(messages, model_name, vpn_tools.tools)
            response = llm_vpn_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=vpn_tools.tools,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            log_gpt_response(response_message, response.choices[0].finish_reason)
            messages.append(response_message)
            
            # Handle tool calls
            if tool_calls:
                print(f"\nGPT calling {len(tool_calls)} tool(s)...\n")
                tool_count = 0
                workflow_completed = False
                guidance_messages = []  # Collect guidance to add AFTER all tool responses
                
                for tool_call in tool_calls:
                    # If workflow already completed, skip remaining tools but add dummy responses
                    if workflow_completed:
                        print(f"Skipping {tool_call.function.name} - workflow already complete")
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_call.function.name,
                            "content": json.dumps({"skipped": True, "reason": "VPN already connected"})
                        })
                        continue
                    
                    result = _execute_tool(tool_call, state)
                    if not result:
                        # Tool execution failed, but we MUST provide a response for this tool_call_id
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_call.function.name,
                            "content": json.dumps({"success": False, "error": f"Tool {tool_call.function.name} execution failed"})
                        })
                        continue
                    
                    # Add tool response to messages
                    messages.append({
                        "tool_call_id": result['tool_call_id'],
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": json.dumps(result['response'])
                    })
                    
                    # Collect guidance message (add AFTER all tool responses)
                    if result['guidance']:
                        guidance_messages.append(result['guidance'])
                    
                    tool_count += 1
                    
                    # Check if workflow is complete after each tool
                    # Set flag to skip remaining tools in this batch
                    if _is_workflow_complete(state):
                        workflow_completed = True
                        print("✅ VPN connection established - skipping remaining tools in batch")
                
                # Add guidance messages AFTER all tool responses are added
                if guidance_messages:
                    combined_guidance = "\n".join(guidance_messages)
                    messages.append({
                        "role": "user",
                        "content": f"Status update: {combined_guidance}"
                    })
                
                print(f"\n✅ Completed {tool_count} tool(s)")
                
                # Return immediately if workflow is complete
                if workflow_completed:
                    print("✅ VPN workflow complete - returning to orchestrator!")
                    log_session_summary(total_requests=1, total_tools=len(state['tools_executed']))
                    return _build_result(state, True, iteration + 1)
                
                print("Continuing to next iteration...\n")
                
            else:
                # No tools called - LLM finished
                final_text = response_message.content
                log_final_response(final_text)
                print(f"\nGPT Response:\n{final_text}\n")
                print("✅ LLM provided final response")
                
                log_session_summary(total_requests=1, total_tools=len(state['tools_executed']))
                return _build_result(state, True, iteration + 1, final_text)
                
        except Exception as e:
            log_error("LLM Execution failed", e)
            print(f"\nCRITICAL ERROR: {str(e)}")
            log_session_summary(total_requests=1, total_tools=len(state['tools_executed']))
            return _build_result(state, False, iteration + 1, error=str(e))
    
    # Max iterations reached
    print(f"\n⚠️  Maximum iterations ({max_iterations}) reached")
    print(f"   Tools executed: {len(state['tools_executed'])}")
    print(f"   VPN Connected: {state['vpn_connected']}")
    print(f"   VPN Disconnected: {state['vpn_disconnected']}")
    
    # Success if VPN was connected (even if not disconnected yet)
    log_session_summary(total_requests=1, total_tools=len(state['tools_executed']))
    return _build_result(state, state['vpn_connected'], max_iterations)


if __name__ == "__main__":
    result = run()
    print("\nExecution Result Summary:")
    print(json.dumps(result, indent=2))
