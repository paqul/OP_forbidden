# LLM Execution Logging System

## Overview
Comprehensive logging system for tracking all LLM execution activities including requests, responses, tool calls, and errors.

## Features

### 📝 What Gets Logged

1. **User Requests** - Every user message sent to the LLM
2. **GPT Requests** - Full details of requests sent to OpenAI API
3. **GPT Responses** - Responses received, including tool call requests
4. **Tool Executions** - Function name, arguments, results, and execution time
5. **Final Responses** - The final answer delivered to the user
6. **Errors** - Any exceptions or errors that occur
7. **Session Summary** - Overview of total requests and tool calls

### 📊 Log Levels

- **INFO** - Important events (shown in console + file)
- **DEBUG** - Detailed debugging info (file only)
- **ERROR** - Errors and exceptions (console + file)

### 📁 Log File Format

Log files are created with timestamps: `llm_execution_2026-04-20_14-30-45.log`

Example log structure:
```
2026-04-20 14:30:45 | INFO     | ================================================
2026-04-20 14:30:45 | INFO     | 🔵 USER REQUEST #1
2026-04-20 14:30:45 | INFO     | Message: Can you list VPN servers?
2026-04-20 14:30:45 | INFO     | ────────────────────────────────────────────────
2026-04-20 14:30:45 | INFO     | 📤 GPT REQUEST
2026-04-20 14:30:45 | INFO     | Model: gpt-4o-mini
2026-04-20 14:30:45 | INFO     | Available Tools: list_vpn_servers, get_vpn_server_status
2026-04-20 14:30:45 | INFO     | ────────────────────────────────────────────────
2026-04-20 14:30:45 | INFO     | 🔧 TOOL EXECUTION: list_vpn_servers
2026-04-20 14:30:45 | INFO     | Arguments: {"region": "us-east"}
2026-04-20 14:30:46 | INFO     | ✅ TOOL RESULT: list_vpn_servers
2026-04-20 14:30:46 | INFO     | Execution Time: 0.234s
2026-04-20 14:30:46 | INFO     | Status: SUCCESS
2026-04-20 14:30:46 | INFO     | Servers Returned: 10
```

## Usage

### Quick Start

```python
from logs.logger_file import (
    log_user_request,
    log_gpt_request,
    log_gpt_response,
    log_tool_call_start,
    log_tool_call_result,
    log_final_response,
    log_error,
    log_session_summary
)

# Log user request
log_user_request("What VPN servers are available?")

# Log GPT request
log_gpt_request(messages, model="gpt-4o-mini", tools=tool_list)

# Log GPT response
log_gpt_response(response_message, finish_reason="tool_calls")

# Log tool execution
log_tool_call_start("list_vpn_servers", {"region": "us-east"})
result = list_vpn_servers(region="us-east")
log_tool_call_result("list_vpn_servers", result, execution_time=0.234)

# Log final response
log_final_response("Here are the available VPN servers...")

# Log errors
try:
    # some code
    pass
except Exception as e:
    log_error("Failed to execute", e)

# Log session summary
log_session_summary(total_requests=5, total_tools=12)
```

### Advanced Usage with LLMLogger Class

```python
from logs.logger_file import LLMLogger
import logging

# Create custom logger with DEBUG level
logger = LLMLogger(log_dir="custom_logs", log_level=logging.DEBUG)

# Use logger methods
logger.log_user_request("Custom request")
logger.log_gpt_request(messages, model="gpt-4o")
# ... etc
```

## Integration

The logging system is already integrated into `llm_execution.py`. Just run:

```bash
python test_logging.py
```

Or use directly:

```python
import llm_execution
llm_execution.run()
```

## Log File Location

All logs are saved to: `logs/llm_execution_YYYY-MM-DD_HH-MM-SS.log`

## Benefits

✅ **Debugging** - Track exactly what happened during execution  
✅ **Monitoring** - See performance metrics (execution time, request count)  
✅ **Audit Trail** - Complete record of all LLM interactions  
✅ **Error Tracking** - Detailed error logs with stack traces  
✅ **Performance Analysis** - Tool execution times and API response times  

## Console Output

The system provides dual output:
- **Console**: Important events (INFO level and above)
- **File**: Everything including DEBUG details

This keeps console clean while maintaining comprehensive file logs.

## Customization

### Change Log Level
```python
from logs.logger_file import LLMLogger
import logging

# Show DEBUG messages in console too
logger = LLMLogger(log_level=logging.DEBUG)
```

### Change Log Directory
```python
logger = LLMLogger(log_dir="my_custom_logs")
```

### Disable Console Output
```python
# Remove console handler from logger
logger.logger.handlers = [h for h in logger.logger.handlers if not isinstance(h, logging.StreamHandler)]
```

## Icons Reference

- 🔵 User Request
- 📤 GPT Request (outgoing)
- 📥 GPT Response (incoming)
- 🔧 Tool Execution
- ✅ Tool Result (success)
- ✨ Final Response
- ❌ Error
- 📊 Session Summary

## Example Session Log

```
================================================================================
LLM Execution Session Started - ID: 2026-04-20_14-30-45
================================================================================
────────────────────────────────────────────────────────────────────────────────
🔵 USER REQUEST #1
Message: Can you list all available VPN servers in the US East region?
────────────────────────────────────────────────────────────────────────────────
📤 GPT REQUEST
Model: gpt-4o-mini
Message Count: 2
Available Tools: list_vpn_servers, get_vpn_server_status, connect_to_vpn
────────────────────────────────────────────────────────────────────────────────
📥 GPT RESPONSE
Finish Reason: tool_calls
Tool Calls Requested: 1
  [1] list_vpn_servers
────────────────────────────────────────────────────────────────────────────────
🔧 TOOL EXECUTION: list_vpn_servers
Arguments: {"region": "us-east"}
✅ TOOL RESULT: list_vpn_servers
Execution Time: 0.234s
Status: SUCCESS
Servers Returned: 10
────────────────────────────────────────────────────────────────────────────────
✨ FINAL RESPONSE
Response: I found 10 available VPN servers in the US East region...
================================================================================
📊 SESSION SUMMARY
Session ID: 2026-04-20_14-30-45
Total Requests: 1
Total Tool Calls: 1
Session Completed
================================================================================
```
