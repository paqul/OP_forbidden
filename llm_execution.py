from keys.projects_api_keys import open_ai_api_key
from prompts.system_prompts import gpt_system_prompt
from openai import OpenAI
import json
import tools

client = OpenAI(api_key=open_ai_api_key)

# Map function names to actual functions
available_functions = {
    "list_vpn_servers": tools.list_vpn_servers,
    "get_vpn_server_status": tools.get_vpn_server_status,
    "connect_to_vpn": tools.connect_to_vpn,
    "disconnect_vpn": tools.disconnect_vpn,
    "get_current_connection_info": tools.get_current_connection_info
}

def run():
    messages = [
        {"role": "system", "content": gpt_system_prompt},
        {"role": "user", "content": "Can you list all available VPN servers in the US East region and tell me which one has the lowest load?"}
    ]
    
    print("Sending request to GPT with VPN tools...")
    gpt_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools.tools,
        tool_choice="auto"
    )
    response_message = gpt_response.choices[0].message
    tool_calls = response_message.tool_calls
    messages.append(response_message)
    
    if tool_calls:
        print(f"\nGPT is calling {len(tool_calls)} tool(s)...\n")
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            print(f"Executing: {function_name}({function_args})")
            if function_name in available_functions:
                function_response = available_functions[function_name](**function_args)
                print(f"Result: {json.dumps(function_response, indent=2)}\n")
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(function_response)
                })
    else:
        answer_clear = response_message.content
        print(f"GPT Response:\n{answer_clear}")
    
    print("\n" + "="*50)
    print("LLM Execution completed.")