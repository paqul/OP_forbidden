from keys.projects_api_keys import open_ai_api_key
from prompts.system_prompts import main_system_prompt
from prompts.user_prompts import inital_orchestrator_prompt
from openai import OpenAI
import json
import time
import vpn_tools
import os
import sys
import llm_vpn_execution
import llm_playwright_execution
from logger.logger_file import (log_user_request, log_gpt_request, log_gpt_response, log_tool_call_start,
    log_tool_call_result, log_final_response, log_error, log_session_summary)


main_client = OpenAI(api_key=open_ai_api_key)

# Define agent tools for the main orchestrator LLM
agent_tools = [
    {
        "type": "function",
        "function": {
            "name": "call_vpn_agent",
            "description": "Delegate VPN-related tasks to a specialized VPN agent. Use this when the user asks to connect/disconnect VPN, list VPN servers, check VPN status, or manage VPN connections. The VPN agent has full access to Mullvad VPN infrastructure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Complete description of the VPN task including ALL details (server location, authentication needs, specific actions)"
                    }
                },
                "required": ["task_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "call_browser_agent",
            "description": "Delegate browser automation and web scraping tasks to a specialized browser agent. IMPORTANT: Include ALL URLs, selectors, and data extraction requirements in task_description. The agent needs complete information to execute.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Complete description of the browser task including ALL details: URLs (full https://...), elements to find, data to extract, screenshots needed, interactions required"
                    }
                },
                "required": ["task_description"]
            }
        }
    }
]

# Available agent functions - Always use task_description (it has all the details)
available_agents = {
    "call_vpn_agent": lambda task_description: llm_vpn_execution.run(task_description),
    "call_browser_agent": lambda task_description: llm_playwright_execution.run(task_description)
}

def main():
    print("Running Main Orchestrator LLM...\n")
    user_message = inital_orchestrator_prompt 
    log_user_request(user_message)
    
    messages = [
        {"role": "system", "content": main_system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    model_name = "gpt-4o"
    max_iterations = 10
    
    for iteration in range(max_iterations):
        print(f"\n{'='*60}")
        print(f"Orchestrator Iteration {iteration + 1}")
        print(f"{'='*60}\n")
        
        log_gpt_request(messages, model_name, agent_tools)
        
        try:
            # Call main orchestrator LLM with agent tools
            gpt_response = main_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=agent_tools,
                tool_choice="auto"
            )
            
            response_message = gpt_response.choices[0].message
            finish_reason = gpt_response.choices[0].finish_reason
            tool_calls = response_message.tool_calls
            
            log_gpt_response(response_message, finish_reason)
            messages.append(response_message)
            
            # Handle agent/tool calls
            if tool_calls:
                print(f"\nOrchestrator is delegating to {len(tool_calls)} agent(s)...\n")
                
                for tool_call in tool_calls:
                    agent_name = tool_call.function.name
                    agent_args = json.loads(tool_call.function.arguments)
                    
                    print(f"🤖 Calling Agent: {agent_name}")
                    print(f"   Task: {agent_args.get('task_description', 'N/A')}\n")
                    
                    log_tool_call_start(agent_name, agent_args)
                    
                    if agent_name in available_agents:
                        start_time = time.time()
                        try:
                            # Execute the agent
                            agent_result = available_agents[agent_name](**agent_args)
                            execution_time = time.time() - start_time
                            
                            log_tool_call_result(agent_name, agent_result, execution_time)
                            
                            print(f"\n✅ Agent '{agent_name}' completed in {execution_time:.2f}s")
                            print(f"   Success: {agent_result.get('success', False)}")
                            print(f"   VPN Connected: {agent_result.get('vpn_connected', False)}")
                            print(f"   VPN Disconnected: {agent_result.get('vpn_disconnected', False)}\n")
                            
                            # Add agent result to messages
                            messages.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": agent_name,
                                "content": json.dumps(agent_result)
                            })
                            
                        except Exception as e:
                            error_msg = f"Agent execution failed: {str(e)}"
                            log_error(agent_name, e)
                            print(f"\n❌ Agent Error: {error_msg}\n")
                            
                            messages.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": agent_name,
                                "content": json.dumps({"success": False, "error": error_msg})
                            })
                    else:
                        error_msg = f"Agent '{agent_name}' not found"
                        print(f"\n❌ {error_msg}\n")
                        log_error(error_msg)
                
                print("Continuing to next iteration...\n")
                
            else:
                # No tool calls - orchestrator provided final response
                final_response = response_message.content
                log_final_response(final_response)
                
                print(f"\n{'='*60}")
                print("ORCHESTRATOR FINAL RESPONSE:")
                print(f"{'='*60}")
                print(final_response)
                print(f"{'='*60}\n")
                
                log_session_summary(total_requests=1, total_tools=0)
                return {"success": True, "response": final_response, "iterations": iteration + 1}
                
        except Exception as e:
            log_error("Main orchestrator failed", e)
            print(f"\n❌ CRITICAL ERROR: {str(e)}\n")
            return {"success": False, "error": str(e), "iterations": iteration + 1}
    
    print(f"\n⚠️  Maximum iterations ({max_iterations}) reached\n")
    return {"success": False, "error": "Max iterations reached", "iterations": max_iterations}

if __name__ == "__main__":
    main()