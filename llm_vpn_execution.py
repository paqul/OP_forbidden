from keys.projects_api_keys import open_ai_api_key, MULLVAD_ACCOUNT
from prompts.system_prompts import vpn_prompt
from openai import OpenAI
import json
import time
import tools
from logger.logger_file import (log_user_request, log_gpt_request, log_gpt_response, log_tool_call_start,
    log_tool_call_result, log_final_response, log_error, log_session_summary)

llm_vpn_client = OpenAI(api_key=open_ai_api_key)

available_functions = {
    "list_vpn_servers": tools.list_vpn_servers,
    "get_vpn_server_status": tools.get_vpn_server_status,
    "connect_to_vpn": tools.connect_to_vpn,
    "disconnect_vpn": tools.disconnect_vpn,
    "get_current_connection_info": tools.get_current_connection_info,
}

# Configuration for tool guidance messages (data-driven approach)
TOOL_GUIDANCE = {
    "list_vpn_servers": {
        "on_success": lambda r: f"✅ Retrieved {r.get('count', 0)} VPN servers. First: {r['servers'][0]['server_id'] if r.get('servers') else 'N/A'}. Next: get_vpn_server_status",
        "check_data": lambda r: r.get('count', 0) > 0
    },
    "get_vpn_server_status": {
        "on_success": lambda r: f"✅ Server {r['data']['server_id']} is {r['data']['status']}. Next: connect_to_vpn(server_id='{r['data']['server_id']}', mullvad_account='...')",
    },
    "connect_to_vpn": {
        "on_success": lambda r: _get_connection_guidance(r),
    },
    "get_current_connection_info": {
        "on_success": lambda r: f"✅ Current IP: {r.get('current_ip', 'Unknown')} ({r.get('country', 'Unknown')}). Next: disconnect_vpn if done",
    },
    "disconnect_vpn": {
        "on_success": lambda r: f"✅ Disconnected from {r.get('disconnect_info', {}).get('tunnel_name', 'Unknown')}. Workflow complete!",
    }
}


def _get_connection_guidance(response):
    """Generate guidance for connect_to_vpn based on connection status."""
    connection = response.get('connection', {})
    server_name = connection.get('server_name', 'Unknown')
    
    if connection.get('test_mode'):
        return f"⚠️ Connected to {server_name} in TEST MODE. Should use production mode with mullvad_account!"
    elif connection.get('authenticated'):
        return f"✅ Connected to {server_name} with authentication. Next: get_current_connection_info"
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
        
        status = "Authenticated ✅" if connection_info.get('authenticated') else "Test mode"
        _print_status_banner("VPN CONNECTION ESTABLISHED!", {
            "Server": connection_info.get('server_name', 'Unknown'),
            "Tunnel": connection_info.get('tunnel_name', 'Unknown'),
            "Status": status
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
    # Return as soon as VPN connection is successful (don't wait for disconnection)
    return state['vpn_connected']


def _build_result(state, success, iterations, final_response=None, error=None):
    """Build execution result dictionary."""
    return {
        "success": success,
        "vpn_connected": state['vpn_connected'],
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
        'vpn_disconnected': False,
        'connection_info': None,
        'disconnect_info': None,
        'tools_executed': [],
    }
    
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
    max_iterations = 5
    
    for iteration in range(max_iterations):
        try:
            # Call LLM
            print(f"\n{'='*60}")
            print(f"Iteration {iteration + 1} - Messages: {len(messages)}")
            print(f"{'='*60}\n")
            
            log_gpt_request(messages, model_name, tools.tools)
            response = llm_vpn_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools.tools,
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
                        continue
                    
                    # Add tool response to messages
                    messages.append({
                        "tool_call_id": result['tool_call_id'],
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": json.dumps(result['response'])
                    })
                    
                    # Add guidance message
                    if result['guidance']:
                        messages.append({
                            "role": "assistant",
                            "content": result['guidance']
                        })
                    
                    tool_count += 1
                    
                    # Check if workflow is complete after each tool
                    # Set flag to skip remaining tools in this batch
                    if _is_workflow_complete(state):
                        workflow_completed = True
                        print("✅ VPN connection established - skipping remaining tools in batch")
                
                print(f"\n✅ Completed {tool_count} tool(s)")
                log_session_summary(total_requests=1, total_tools=tool_count)
                
                # Return immediately if workflow is complete
                if workflow_completed:
                    print("✅ VPN workflow complete - returning to orchestrator!")
                    return _build_result(state, True, iteration + 1)
                
                print("Continuing to next iteration...\n")
                
            else:
                # No tools called - LLM finished
                final_text = response_message.content
                log_final_response(final_text)
                print(f"\nGPT Response:\n{final_text}\n")
                print("✅ LLM provided final response")
                
                return _build_result(state, True, iteration + 1, final_text)
                
        except Exception as e:
            log_error("LLM Execution failed", e)
            print(f"\nCRITICAL ERROR: {str(e)}")
            return _build_result(state, False, iteration + 1, error=str(e))
    
    # Max iterations reached
    print(f"\n⚠️  Maximum iterations ({max_iterations}) reached")
    print(f"   Tools executed: {len(state['tools_executed'])}")
    print(f"   VPN Connected: {state['vpn_connected']}")
    print(f"   VPN Disconnected: {state['vpn_disconnected']}")
    
    # Success if VPN was connected (even if not disconnected yet)
    return _build_result(state, state['vpn_connected'], max_iterations)


if __name__ == "__main__":
    result = run()
    print("\nExecution Result Summary:")
    print(json.dumps(result, indent=2))
