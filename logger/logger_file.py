import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional


class LLMLogger:
    """
    Comprehensive logger for LLM execution tracking.
    Logs requests, responses, tool calls, and errors with structured formatting.
    """
    
    def __init__(self, log_dir: str = "logs", log_level: int = logging.INFO):
        """
        Initialize the LLM Logger.
        
        Args:
            log_dir: Directory to store log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_dir = log_dir
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create logger instance
        self.logger = logging.getLogger('LLMExecution')
        self.logger.setLevel(log_level)
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_filename = os.path.join(log_dir, f'llm_execution_{timestamp}.log')
        
        # File handler - detailed logs
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler - important logs only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Session tracking
        self.session_id = timestamp
        self.request_count = 0
        
        self.logger.info("="*80)
        self.logger.info(f"LLM Execution Session Started - ID: {self.session_id}")
        self.logger.info("="*80)
    
    def _format_json(self, data: Any, max_length: int = 1000) -> str:
        """Format JSON data for logging with optional truncation."""
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            if len(json_str) > max_length:
                return json_str[:max_length] + f"\n... (truncated, total length: {len(json_str)})"
            return json_str
        except Exception:
            return str(data)
    
    def log_user_request(self, user_message: str):
        """Log the initial user request."""
        self.request_count += 1
        self.logger.info("─" * 80)
        self.logger.info(f"🔵 USER REQUEST #{self.request_count}")
        self.logger.info(f"Message: {user_message}")
        self.logger.debug(f"Request Count: {self.request_count}")
    
    def log_gpt_request(self, messages: List[Dict], model: str, tools: Optional[List] = None):
        """Log the request being sent to GPT."""
        self.logger.info("─" * 80)
        self.logger.info(f"📤 GPT REQUEST")
        self.logger.info(f"Model: {model}")
        self.logger.info(f"Message Count: {len(messages)}")
        
        if tools:
            tool_names = [t.get('function', {}).get('name', 'unknown') for t in tools]
            self.logger.info(f"Available Tools: {', '.join(tool_names)}")
        
        # Log full messages to debug level
        self.logger.debug("Full Messages:")
        for i, msg in enumerate(messages):
            # Handle both dict and ChatCompletionMessage object
            if isinstance(msg, dict):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
            else:
                # It's a ChatCompletionMessage object (Pydantic model)
                role = getattr(msg, 'role', 'unknown')
                content = getattr(msg, 'content', '') or ''
            
            self.logger.debug(f"  [{i}] {role}: {content[:200]}{'...' if len(str(content)) > 200 else ''}")
    
    def log_gpt_response(self, response_message: Any, finish_reason: str = None):
        """Log the response received from GPT."""
        self.logger.info("─" * 80)
        self.logger.info(f"📥 GPT RESPONSE")
        
        if finish_reason:
            self.logger.info(f"Finish Reason: {finish_reason}")
        
        # Check for tool calls
        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            self.logger.info(f"Tool Calls Requested: {len(response_message.tool_calls)}")
            for i, tool_call in enumerate(response_message.tool_calls, 1):
                self.logger.info(f"  [{i}] {tool_call.function.name}")
        
        # Check for content
        if hasattr(response_message, 'content') and response_message.content:
            content = str(response_message.content)
            if len(content) > 500:
                self.logger.info(f"Content: {content[:500]}... (truncated)")
                self.logger.debug(f"Full Content: {content}")
            else:
                self.logger.info(f"Content: {content}")
    
    def log_tool_call_start(self, function_name: str, arguments: Dict):
        """Log when a tool is about to be executed."""
        self.logger.info("─" * 80)
        self.logger.info(f"🔧 TOOL EXECUTION: {function_name}")
        self.logger.info(f"Arguments: {self._format_json(arguments, max_length=500)}")
    
    def log_tool_call_result(self, function_name: str, result: Any, execution_time: float = None):
        """Log the result of a tool execution."""
        self.logger.info(f"✅ TOOL RESULT: {function_name}")
        
        if execution_time:
            self.logger.info(f"Execution Time: {execution_time:.3f}s")
        
        # Check if result is a dict with success field
        if isinstance(result, dict):
            if 'success' in result:
                status = "SUCCESS" if result['success'] else "FAILED"
                self.logger.info(f"Status: {status}")
            
            if 'error' in result and result.get('error'):
                self.logger.error(f"Error: {result['error']}")
        
        # Log result details
        self.logger.debug(f"Full Result: {self._format_json(result)}")
        
        # Log summary for common result structures
        if isinstance(result, dict):
            if 'count' in result:
                self.logger.info(f"Result Count: {result['count']}")
            if 'servers' in result and isinstance(result['servers'], list):
                self.logger.info(f"Servers Returned: {len(result['servers'])}")
    
    def log_final_response(self, response: str):
        """Log the final response to the user."""
        self.logger.info("─" * 80)
        self.logger.info(f"✨ FINAL RESPONSE")
        self.logger.info(f"Response: {response}")
    
    def log_error(self, error_msg: str, exception: Exception = None):
        """Log an error that occurred during execution."""
        self.logger.error("─" * 80)
        self.logger.error(f"❌ ERROR: {error_msg}")
        
        if exception:
            self.logger.error(f"Exception Type: {type(exception).__name__}")
            self.logger.error(f"Exception Details: {str(exception)}")
            self.logger.debug("Full Traceback:", exc_info=True)
    
    def log_session_summary(self, total_requests: int = None, total_tools: int = None):
        """Log a summary at the end of the session."""
        self.logger.info("="*80)
        self.logger.info("📊 SESSION SUMMARY")
        self.logger.info(f"Session ID: {self.session_id}")
        
        if total_requests is not None:
            self.logger.info(f"Total Requests: {total_requests}")
        else:
            self.logger.info(f"Total Requests: {self.request_count}")
        
        if total_tools is not None:
            self.logger.info(f"Total Tool Calls: {total_tools}")
        
        self.logger.info("Session Completed")
        self.logger.info("="*80)


# Create a global logger instance that can be imported
llm_logger = LLMLogger()


# Convenience functions for quick logging
def log_user_request(user_message: str):
    """Quick log user request."""
    llm_logger.log_user_request(user_message)


def log_gpt_request(messages: List[Dict], model: str, tools: Optional[List] = None):
    """Quick log GPT request."""
    llm_logger.log_gpt_request(messages, model, tools)


def log_gpt_response(response_message: Any, finish_reason: str = None):
    """Quick log GPT response."""
    llm_logger.log_gpt_response(response_message, finish_reason)


def log_tool_call_start(function_name: str, arguments: Dict):
    """Quick log tool call start."""
    llm_logger.log_tool_call_start(function_name, arguments)


def log_tool_call_result(function_name: str, result: Any, execution_time: float = None):
    """Quick log tool call result."""
    llm_logger.log_tool_call_result(function_name, result, execution_time)


def log_final_response(response: str):
    """Quick log final response."""
    llm_logger.log_final_response(response)


def log_error(error_msg: str, exception: Exception = None):
    """Quick log error."""
    llm_logger.log_error(error_msg, exception)


def log_session_summary(total_requests: int = None, total_tools: int = None):
    """Quick log session summary."""
    llm_logger.log_session_summary(total_requests, total_tools)
