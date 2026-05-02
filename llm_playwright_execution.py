from keys.projects_api_keys import open_ai_api_key
from prompts.system_prompts import playwright_prompt
from openai import OpenAI
import json
import time
import random
import playwright_tools
from logger.logger_file import (log_user_request, log_gpt_request, log_gpt_response, log_tool_call_start,
    log_tool_call_result, log_final_response, log_error, log_session_summary)

llm_playwright_client = OpenAI(api_key=open_ai_api_key)

# Anti-bot detection: Random delays before operations (seconds)
MIN_DELAY = 2
MAX_DELAY = 12

# Functions that should have human-like delays
DELAYED_FUNCTIONS = {
    "navigate_to_url",
    "click_element",
    "type_text",
    "handle_consent_dialog",
}

available_functions = {
    "launch_browser": playwright_tools.launch_browser,
    "navigate_to_url": playwright_tools.navigate_to_url,
    "click_element": playwright_tools.click_element,
    "type_text": playwright_tools.type_text,
    "extract_text": playwright_tools.extract_text,
    "take_screenshot": playwright_tools.take_screenshot,
    "wait_for_element": playwright_tools.wait_for_element,
    "get_page_info": playwright_tools.get_page_info,
    "close_browser": playwright_tools.close_browser,
    "execute_javascript": playwright_tools.execute_javascript,
    "reset_timeout_counter": playwright_tools.reset_timeout_counter,
    "wait_for_duration": playwright_tools.wait_for_duration,
    "handle_consent_dialog": playwright_tools.handle_consent_dialog,
    "check_for_bot_detection": playwright_tools.check_for_bot_detection,
    "get_video_duration": playwright_tools.get_video_duration,
}

# Configuration for tool guidance messages (data-driven approach)
TOOL_GUIDANCE = {
    "launch_browser": {
        "on_success": lambda r: f"✅ Browser launched: {r.get('browser_type', 'unknown')} ({r.get('viewport', 'unknown')})",
    },
    "navigate_to_url": {
        "on_success": lambda r: f"✅ Navigated to: {r.get('title', 'Page')} (Status: {r.get('status', 'unknown')})",
    },
    "click_element": {
        "on_success": lambda r: f"✅ Clicked: {r.get('selector', 'element')}",
    },
    "type_text": {
        "on_success": lambda r: f"✅ Typed {r.get('text_length', 0)} characters into {r.get('selector', 'field')}",
    },
    "extract_text": {
        "on_success": lambda r: _get_extraction_guidance(r),
    },
    "take_screenshot": {
        "on_success": lambda r: f"✅ Screenshot saved: {r.get('filename', 'unknown')} ({r.get('type', 'unknown')})",
    },
    "wait_for_element": {
        "on_success": lambda r: f"✅ Element ready: {r.get('selector', 'unknown')} is {r.get('state', 'visible')}",
    },
    "get_page_info": {
        "on_success": lambda r: f"✅ Page: {r.get('title', 'Unknown')} at {r.get('url', 'unknown')}",
    },
    "close_browser": {
        "on_success": lambda r: f"✅ Browser closed. Cleaned up: {', '.join(r.get('closed', []))}",
    },
    "execute_javascript": {
        "on_success": lambda r: f"✅ JavaScript executed. Result: {str(r.get('result', 'None'))[:100]}",
    },
    "reset_timeout_counter": {
        "on_success": lambda r: f"✅ Timeout counter reset (was: {r.get('previous_count', 0)})",
    },
    "wait_for_duration": {
        "on_success": lambda r: f"✅ Waited {r.get('elapsed_seconds', 0)} seconds ({r.get('checks_performed', 0)} checks performed)",
    },
    "handle_consent_dialog": {
        "on_success": lambda r: f"✅ Consent dialog: {r.get('message', 'handled')}" if r.get('found', True) else f"ℹ️  No consent dialog found",
    },
    "check_for_bot_detection": {
        "on_success": lambda r: f"✅ No bot detection found - page is accessible",
    },
    "get_video_duration": {
        "on_success": lambda r: f"✅ Video duration: {r.get('duration', 'unknown')} ({r.get('total_seconds', 0)} seconds)",
    }
}


def _get_extraction_guidance(response):
    """Generate guidance for text extraction based on results."""
    if response.get('count'):
        return f"✅ Extracted text from {response.get('count')} elements"
    else:
        text_preview = str(response.get('text', ''))[:100]
        return f"✅ Extracted text: {text_preview}{'...' if len(str(response.get('text', ''))) > 100 else ''}"


def _generate_guidance_message(function_name, function_response):
    """Generate contextual guidance message for LLM based on tool execution."""
    if not function_response.get('success', True):
        error_msg = function_response.get('error', 'Unknown error')
        return f"❌ {function_name} failed: {error_msg}"
    
    tool_config = TOOL_GUIDANCE.get(function_name)
    if not tool_config:
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


def _track_browser_status(function_name, response, state):
    """Track browser launch/close status and print banners."""
    if function_name == "launch_browser" and response.get('success'):
        state['browser_launched'] = True
        state['browser_type'] = response.get('browser_type', 'unknown')
        
        _print_status_banner("BROWSER LAUNCHED!", {
            "Type": response.get('browser_type', 'unknown'),
            "Mode": 'Headless' if response.get('headless') else 'Headed',
            "Viewport": response.get('viewport', 'unknown')
        })
    
    elif function_name == "navigate_to_url" and response.get('success'):
        state['current_url'] = response.get('url')
        state['current_title'] = response.get('title')
    
    elif function_name == "close_browser" and response.get('success'):
        state['browser_closed'] = True
        
        _print_status_banner("BROWSER CLOSED!", {
            "Cleaned": ', '.join(response.get('closed', []))
        })


def _execute_tool(tool_call, state):
    """Execute a single tool call and handle results."""
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)
    
    # Add random human-like delay before certain operations.
    # Skip the delay if this is a retry of a recently failed call with the same function.
    last_same_call = next(
        (t for t in reversed(state['tools_executed']) if t['name'] == function_name),
        None
    )
    is_retry = last_same_call is not None and not last_same_call['success']
    if function_name in DELAYED_FUNCTIONS and not is_retry:
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        print(f"\n⏱️  Human-like delay: {delay:.1f} seconds (avoiding bot detection)...")
        time.sleep(delay)
    elif is_retry and function_name in DELAYED_FUNCTIONS:
        print(f"\n⚡ Skipping delay — retrying failed {function_name}")
    
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
        
        # Track browser status changes
        _track_browser_status(function_name, response, state)
        
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
        # Return error response with tool_call_id to prevent API errors
        return {
            "tool_call_id": tool_call.id,
            "response": {"success": False, "error": str(e)},
            "guidance": f"❌ {function_name} failed: {str(e)}"
        }


def _is_workflow_complete(state, user_message):
    """Check if browser automation workflow is complete."""
    # Don't auto-complete - let orchestrator control lifecycle
    # Only return True if explicitly told to finish
    return False


def _build_result(state, success, iterations, final_response=None, error=None):
    """Build execution result dictionary."""
    return {
        "success": success,
        "browser_launched": state['browser_launched'],
        "browser_closed": state['browser_closed'],
        "current_url": state.get('current_url'),
        "current_title": state.get('current_title'),
        "final_response": final_response,
        "tools_executed": state['tools_executed'],
        "error": error,
        "iterations": iterations
    }


def run(user_message: str = None):
    """Execute LLM-driven browser automation workflow."""
    # Initialize state
    state = {
        'browser_launched': False,
        'browser_closed': False,
        'current_url': None,
        'current_title': None,
        'tools_executed': [],
    }
    
    # Setup initial message
    if not user_message:
        user_message = "Launch a browser and navigate to https://www.example.com"
    
    log_user_request(user_message)
    
    # Build system prompt
    system_prompt = playwright_prompt
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    # Main execution loop
    model_name = "gpt-4o"
    max_iterations = 20
    
    for iteration in range(max_iterations):
        try:
            # Call LLM
            print(f"\n{'='*60}")
            print(f"Iteration {iteration + 1} - Messages: {len(messages)}")
            print(f"{'='*60}\n")
            
            log_gpt_request(messages, model_name, playwright_tools.tools)
            response = llm_playwright_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=playwright_tools.tools,
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
                guidance_messages = []  # Collect guidance to add AFTER all tool responses
                
                for tool_call in tool_calls:
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
                
                # Add guidance messages AFTER all tool responses are added
                if guidance_messages:
                    combined_guidance = "\n".join(guidance_messages)
                    messages.append({
                        "role": "user",
                        "content": f"Status update: {combined_guidance}"
                    })
                
                print(f"\n✅ Completed {tool_count} tool(s)")
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
    
    # Max iterations reached — ensure browser is released
    print(f"\n⚠️  Maximum iterations ({max_iterations}) reached")
    print(f"   Tools executed: {len(state['tools_executed'])}")
    print(f"   Browser launched: {state['browser_launched']}")
    print(f"   Browser closed: {state['browser_closed']}")
    if state['browser_launched'] and not state['browser_closed']:
        print("   🧹 Closing browser to free resources...")
        try:
            playwright_tools.close_browser()
            state['browser_closed'] = True
        except Exception:
            pass
    
    log_session_summary(total_requests=1, total_tools=len(state['tools_executed']))
    return _build_result(state, state['browser_launched'], max_iterations)


if __name__ == "__main__":
    result = run()
    print("\nExecution Result Summary:")
    print(json.dumps(result, indent=2))
