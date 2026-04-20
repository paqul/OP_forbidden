from keys.projects_api_keys import open_ai_api_key
from prompts.system_prompts import gpt_system_prompt
from openai import OpenAI
import json
import time
import tools
from logger.logger_file import (log_user_request, log_gpt_request, log_gpt_response, log_tool_call_start,
    log_tool_call_result, log_final_response, log_error, log_session_summary)

client = OpenAI(api_key=open_ai_api_key)

available_functions = {
    "list_vpn_servers": tools.list_vpn_servers,
    "get_vpn_server_status": tools.get_vpn_server_status,
    "connect_to_vpn": tools.connect_to_vpn,
    "disconnect_vpn": tools.disconnect_vpn,
    "get_current_connection_info": tools.get_current_connection_info
}

def run():
    cnt = 0
    while True:
        try:
            user_message = "Can you list all available VPN servers in any region and try connect to one of them? Also, check the connection info and disconnect after."
            log_user_request(user_message)
            messages = [
                {"role": "system", "content": gpt_system_prompt},
                {"role": "user", "content": user_message}
            ]
            model_name = "gpt-4o-mini"
            log_gpt_request(messages, model_name, tools.tools)
            print("Sending request to GPT with VPN tools...")
            gpt_response = client.chat.completions.create(
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
                second_response = client.chat.completions.create(
                    model=model_name,
                    messages=messages
                )
                final_message = second_response.choices[0].message
                log_gpt_response(final_message, second_response.choices[0].finish_reason)
                if final_message.content:
                    log_final_response(final_message.content)
                    print(f"\nFinal GPT Response:\n{final_message.content}")
            else:
                answer_clear = response_message.content
                log_final_response(answer_clear)
                print(f"GPT Response:\n{answer_clear}")
            print("\n" + "="*50)
            print("LLM Execution completed.")
            log_session_summary(total_requests=1, total_tools=tool_call_count)
        except Exception as e:
            log_error("LLM Execution failed", e)
            print(f"\nCRITICAL ERROR: {str(e)}")
            raise
        cnt += 1
        if cnt >= 2:
            break