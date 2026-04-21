from keys.projects_api_keys import open_ai_api_key
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
    "test_vpn_connection": tools.test_vpn_connection
}

def run(user_message: str = None): #here should be user_message as argument, but for testing we will use a fixed message
    cnt = 0
    vpn_connected = False  # Track VPN connection status
    vpn_disconnected = False  # Track VPN disconnection status
    
    # Collect execution results for return
    execution_result = {
        "success": False,
        "vpn_connected": False,
        "vpn_disconnected": False,
        "connection_info": None,
        "disconnect_info": None,
        "final_response": None,
        "tools_executed": [],
        "error": None,
        "iterations": 0
    }
    
    while True:
        try:
            user_message = "Can you list all available VPN servers in any region and try connect to one of them? Also, check the connection info and disconnect after."
            # user_message = user_message # NORMAL RUN
            log_user_request(user_message)
            messages = [
                {"role": "system", "content": vpn_prompt},
                {"role": "user", "content": user_message}
            ]
            model_name = "gpt-4o-mini"
            log_gpt_request(messages, model_name, tools.tools)
            print("Sending request to GPT with VPN tools...")
            gpt_response = llm_vpn_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools.tools,
                tool_choice="auto"
            )
            response_message = gpt_response.choices[0].message
            finish_reason = gpt_response.choices[0].finish_reason
            tool_calls = response_message.tool_calls
            log_gpt_response(response_message, finish_reason)
            messages.append(response_message)
            tool_call_count = 0
            
            if tool_calls:
                print(f"\nGPT is calling {len(tool_calls)} tool(s)...\n")
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    log_tool_call_start(function_name, function_args)
                    print(f"Executing: {function_name}({function_args})")
                    if function_name in available_functions:
                        start_time = time.time()
                        try:
                            function_response = available_functions[function_name](**function_args)
                            execution_time = time.time() - start_time
                            log_tool_call_result(function_name, function_response, execution_time)
                            print(f"Result: {json.dumps(function_response, indent=2)}\n")
                            
                            # Check if VPN connection was successfully established
                            if function_name == "connect_to_vpn" and function_response.get('success'):
                                vpn_connected = True
                                connection_info = function_response.get('connection', {})
                                execution_result['vpn_connected'] = True
                                execution_result['connection_info'] = connection_info
                                print(f"\n{'='*60}")
                                print(f"✅ VPN CONNECTION ESTABLISHED!")
                                print(f"   Server: {connection_info.get('server_name', 'Unknown')}")
                                print(f"   Tunnel: {connection_info.get('tunnel_name', 'Unknown')}")
                                if connection_info.get('authenticated'):
                                    print(f"   Status: Authenticated with Mullvad ✅")
                                elif connection_info.get('test_mode'):
                                    print(f"   Status: Test mode (safe)")
                                print(f"{'='*60}\n")
                            
                            # Check if VPN was successfully disconnected
                            if function_name == "disconnect_vpn" and function_response.get('success'):
                                vpn_disconnected = True
                                disconnect_info = function_response.get('disconnect_info', {})
                                execution_result['vpn_disconnected'] = True
                                execution_result['disconnect_info'] = disconnect_info
                                print(f"\n{'='*60}")
                                print(f"✅ VPN DISCONNECTED SUCCESSFULLY!")
                                print(f"   Tunnel: {disconnect_info.get('tunnel_name', 'Unknown')}")
                                print(f"   Status: {disconnect_info.get('status', 'Unknown')}")
                                if disconnect_info.get('tunnel_removed'):
                                    print(f"   Cleanup: Tunnel removed completely ✅")
                                print(f"{'='*60}\n")
                            
                            # Track tool execution
                            execution_result['tools_executed'].append({
                                "name": function_name,
                                "args": function_args,
                                "success": function_response.get('success', True),
                                "execution_time": execution_time
                            })
                            
                            messages.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": json.dumps(function_response)
                            })
                            tool_call_count += 1
                        except Exception as e:
                            log_error(f"Tool execution failed: {function_name}", e)
                            print(f"ERROR executing {function_name}: {str(e)}\n")
                    else:
                        error_msg = f"Function {function_name} not found in available_functions"
                        log_error(error_msg)
                        print(f"ERROR: {error_msg}\n")
                print("Getting final response from GPT...")
                log_gpt_request(messages, model_name, tools.tools)
                second_response = llm_vpn_client.chat.completions.create(
                    model=model_name,
                    messages=messages
                )
                final_message = second_response.choices[0].message
                log_gpt_response(final_message, second_response.choices[0].finish_reason)
                if final_message.content:
                    log_final_response(final_message.content)
                    print(f"\nFinal GPT Response:\n{final_message.content}")
                    execution_result['final_response'] = final_message.content
            else:
                answer_clear = response_message.content
                log_final_response(answer_clear)
                print(f"GPT Response:\n{answer_clear}")
                execution_result['final_response'] = answer_clear
            print("\n" + "="*50)
            print("LLM Execution completed.")
            log_session_summary(total_requests=1, total_tools=tool_call_count)
            
            execution_result['success'] = True
            execution_result['iterations'] = cnt + 1
            
            # Break if VPN was successfully connected or disconnected
            if vpn_connected:
                print("\n✅ Breaking loop: VPN connection established successfully!")
                return execution_result
            if vpn_disconnected:
                print("\n✅ Breaking loop: VPN disconnected successfully!")
                return execution_result
                
        except Exception as e:
            log_error("LLM Execution failed", e)
            print(f"\nCRITICAL ERROR: {str(e)}")
            execution_result['success'] = False
            execution_result['error'] = str(e)
            execution_result['iterations'] = cnt + 1
            return execution_result
            
        cnt += 1
        if cnt >= 5:
            print("\n⚠️  Breaking loop: Maximum iterations reached (safety limit)")
            execution_result['iterations'] = cnt
            return execution_result