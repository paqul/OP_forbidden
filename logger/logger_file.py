import logging
import logging.handlers
import os
import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional


# Secrets to redact from all log output.  Populated lazily on first use.
_REDACT_PATTERNS: list[re.Pattern] = []

def _load_redact_patterns() -> list[re.Pattern]:
    """Build redaction patterns from environment/.env at log-time (avoids import cycles)."""
    if _REDACT_PATTERNS:
        return _REDACT_PATTERNS
    try:
        from keys.projects_api_keys import open_ai_api_key, MULLVAD_ACCOUNT
        for secret in (open_ai_api_key, MULLVAD_ACCOUNT):
            if secret and len(secret) > 4:
                _REDACT_PATTERNS.append(re.compile(re.escape(secret)))
    except Exception:
        pass
    return _REDACT_PATTERNS


def _redact(text: str) -> str:
    """Replace known secrets with '[REDACTED]' in a string."""
    for pattern in _load_redact_patterns():
        text = pattern.sub("[REDACTED]", text)
    return text


class LLMLogger:
    """
    Comprehensive logger for LLM execution tracking.
    Logs requests, responses, tool calls, and errors with structured formatting.
    Uses rotating file handler (10 MB per file, keeps 5 backups).
    Automatically redacts API keys and account numbers from all output.
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

        # Rotating file handler — 10 MB per file, keep 5 backups
        file_handler = logging.handlers.RotatingFileHandler(
            log_filename, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
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

    def _safe_log(self, level: int, message: str):
        """Log a message after redacting secrets."""
        self.logger.log(level, _redact(message))


    def _format_json(self, data: Any, max_length: int = 1000) -> str:
        """Format JSON data for logging with optional truncation."""
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            if len(json_str) > max_length:
                return json_str[:max_length] + f"\n... (truncated, total length: {len(json_str)})"
            return _redact(json_str)
        except Exception:
            return _redact(str(data))

    def log_user_request(self, user_message: str):
        """Log the initial user request."""
        self.request_count += 1
        self._safe_log(logging.INFO, "─" * 80)
        self._safe_log(logging.INFO, f"🔵 USER REQUEST #{self.request_count}")
        self._safe_log(logging.INFO, f"Message: {user_message}")
        self._safe_log(logging.DEBUG, f"Request Count: {self.request_count}")

    def log_gpt_request(self, messages: List[Dict], model: str, tools: Optional[List] = None):
        """Log the request being sent to GPT."""
        self._safe_log(logging.INFO, "─" * 80)
        self._safe_log(logging.INFO, f"📤 GPT REQUEST")
        self._safe_log(logging.INFO, f"Model: {model}")
        self._safe_log(logging.INFO, f"Message Count: {len(messages)}")

        if tools:
            tool_names = [t.get('function', {}).get('name', 'unknown') for t in tools]
            self._safe_log(logging.INFO, f"Available Tools: {', '.join(tool_names)}")

        # Log full messages to debug level
        self._safe_log(logging.DEBUG, "Full Messages:")
        for i, msg in enumerate(messages):
            if isinstance(msg, dict):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
            else:
                role = getattr(msg, 'role', 'unknown')
                content = getattr(msg, 'content', '') or ''
            self._safe_log(logging.DEBUG, f"  [{i}] {role}: {str(content)[:200]}{'...' if len(str(content)) > 200 else ''}")

    def log_gpt_response(self, response_message: Any, finish_reason: str = None):
        """Log the response received from GPT."""
        self._safe_log(logging.INFO, "─" * 80)
        self._safe_log(logging.INFO, f"📥 GPT RESPONSE")

        if finish_reason:
            self._safe_log(logging.INFO, f"Finish Reason: {finish_reason}")

        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            self._safe_log(logging.INFO, f"Tool Calls Requested: {len(response_message.tool_calls)}")
            for i, tool_call in enumerate(response_message.tool_calls, 1):
                self._safe_log(logging.INFO, f"  [{i}] {tool_call.function.name}")

        if hasattr(response_message, 'content') and response_message.content:
            content = str(response_message.content)
            if len(content) > 500:
                self._safe_log(logging.INFO, f"Content: {content[:500]}... (truncated)")
                self._safe_log(logging.DEBUG, f"Full Content: {content}")
            else:
                self._safe_log(logging.INFO, f"Content: {content}")

    def log_tool_call_start(self, function_name: str, arguments: Dict):
        """Log when a tool is about to be executed."""
        self._safe_log(logging.INFO, "─" * 80)
        self._safe_log(logging.INFO, f"🔧 TOOL EXECUTION: {function_name}")
        self._safe_log(logging.INFO, f"Arguments: {self._format_json(arguments, max_length=500)}")

    def log_tool_call_result(self, function_name: str, result: Any, execution_time: float = None):
        """Log the result of a tool execution."""
        self._safe_log(logging.INFO, f"✅ TOOL RESULT: {function_name}")

        if execution_time:
            self._safe_log(logging.INFO, f"Execution Time: {execution_time:.3f}s")

        if isinstance(result, dict):
            if 'success' in result:
                status = "SUCCESS" if result['success'] else "FAILED"
                self._safe_log(logging.INFO, f"Status: {status}")
            if 'error' in result and result.get('error'):
                self._safe_log(logging.ERROR, f"Error: {result['error']}")

        self._safe_log(logging.DEBUG, f"Full Result: {self._format_json(result)}")

        if isinstance(result, dict):
            if 'count' in result:
                self._safe_log(logging.INFO, f"Result Count: {result['count']}")
            if 'servers' in result and isinstance(result['servers'], list):
                self._safe_log(logging.INFO, f"Servers Returned: {len(result['servers'])}")

    def log_final_response(self, response: str):
        """Log the final response to the user."""
        self._safe_log(logging.INFO, "─" * 80)
        self._safe_log(logging.INFO, f"✨ FINAL RESPONSE")
        self._safe_log(logging.INFO, f"Response: {response}")

    def log_error(self, error_msg: str, exception: Exception = None):
        """Log an error that occurred during execution."""
        self._safe_log(logging.ERROR, "─" * 80)
        self._safe_log(logging.ERROR, f"❌ ERROR: {error_msg}")
        if exception:
            self._safe_log(logging.ERROR, f"Exception Type: {type(exception).__name__}")
            self._safe_log(logging.ERROR, f"Exception Details: {_redact(str(exception))}")
            self.logger.debug("Full Traceback:", exc_info=True)

    def log_session_summary(self, total_requests: int = None, total_tools: int = None):
        """Log a summary at the end of the session."""
        self._safe_log(logging.INFO, "="*80)
        self._safe_log(logging.INFO, "📊 SESSION SUMMARY")
        self._safe_log(logging.INFO, f"Session ID: {self.session_id}")
        if total_requests is not None:
            self._safe_log(logging.INFO, f"Total Requests: {total_requests}")
        else:
            self._safe_log(logging.INFO, f"Total Requests: {self.request_count}")
        if total_tools is not None:
            self._safe_log(logging.INFO, f"Total Tool Calls: {total_tools}")
        self._safe_log(logging.INFO, "Session Completed")
        self._safe_log(logging.INFO, "="*80)


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
