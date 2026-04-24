"""
Comprehensive test suite for llm_playwright_execution.py

Tests cover:
1. Helper functions (guidance generation, state tracking)
2. Tool execution with mocked tools
3. State management and result building
4. Error handling scenarios
5. Integration with real LLM (optional)
"""

import sys
import os
import io
import json
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import llm_playwright_execution


# ============================================================================
# Test Helper Functions
# ============================================================================

def test_get_extraction_guidance():
    """Test text extraction guidance generation."""
    print("\n" + "="*60)
    print("TEST: _get_extraction_guidance()")
    print("="*60 + "\n")
    
    passed = True
    
    # Test 1: Multiple elements extracted
    response1 = {"count": 5, "texts": ["a", "b", "c", "d", "e"]}
    result1 = llm_playwright_execution._get_extraction_guidance(response1)
    expected1 = "✅ Extracted text from 5 elements"
    if result1 == expected1:
        print(f"✅ Test 1 PASSED: Multiple elements - '{result1}'")
    else:
        print(f"❌ Test 1 FAILED: Expected '{expected1}', got '{result1}'")
        passed = False
    
    # Test 2: Single element with short text
    response2 = {"text": "Short text"}
    result2 = llm_playwright_execution._get_extraction_guidance(response2)
    expected2 = "✅ Extracted text: Short text"
    if result2 == expected2:
        print(f"✅ Test 2 PASSED: Short text - '{result2}'")
    else:
        print(f"❌ Test 2 FAILED: Expected '{expected2}', got '{result2}'")
        passed = False
    
    # Test 3: Single element with long text (should truncate)
    long_text = "A" * 150
    response3 = {"text": long_text}
    result3 = llm_playwright_execution._get_extraction_guidance(response3)
    if result3.startswith("✅ Extracted text:") and result3.endswith("..."):
        print(f"✅ Test 3 PASSED: Long text truncated - '{result3[:50]}...'")
    else:
        print(f"❌ Test 3 FAILED: Long text should be truncated with '...'")
        passed = False
    
    print(f"\n{'='*60}")
    print(f"{'✅ ALL TESTS PASSED' if passed else '❌ SOME TESTS FAILED'}")
    print(f"{'='*60}\n")
    
    return passed


def test_generate_guidance_message():
    """Test guidance message generation for various tools."""
    print("\n" + "="*60)
    print("TEST: _generate_guidance_message()")
    print("="*60 + "\n")
    
    passed = True
    
    # Test 1: Successful launch_browser
    response1 = {
        "success": True,
        "browser_type": "chromium",
        "viewport": "1920x1080"
    }
    result1 = llm_playwright_execution._generate_guidance_message("launch_browser", response1)
    if "chromium" in result1 and "1920x1080" in result1:
        print(f"✅ Test 1 PASSED: launch_browser - '{result1}'")
    else:
        print(f"❌ Test 1 FAILED: Should include browser_type and viewport")
        passed = False
    
    # Test 2: Failed tool execution
    response2 = {
        "success": False,
        "error": "Browser not installed"
    }
    result2 = llm_playwright_execution._generate_guidance_message("launch_browser", response2)
    if "failed" in result2.lower() and "Browser not installed" in result2:
        print(f"✅ Test 2 PASSED: Failed tool - '{result2}'")
    else:
        print(f"❌ Test 2 FAILED: Should indicate failure with error message")
        passed = False
    
    # Test 3: Successful navigate_to_url
    response3 = {
        "success": True,
        "title": "Example Domain",
        "status": 200
    }
    result3 = llm_playwright_execution._generate_guidance_message("navigate_to_url", response3)
    if "Example Domain" in result3 and "200" in result3:
        print(f"✅ Test 3 PASSED: navigate_to_url - '{result3}'")
    else:
        print(f"❌ Test 3 FAILED: Should include title and status")
        passed = False
    
    # Test 4: Successful take_screenshot
    response4 = {
        "success": True,
        "filename": "test_screenshot.png",
        "type": "viewport"
    }
    result4 = llm_playwright_execution._generate_guidance_message("take_screenshot", response4)
    if "test_screenshot.png" in result4 and "viewport" in result4:
        print(f"✅ Test 4 PASSED: take_screenshot - '{result4}'")
    else:
        print(f"❌ Test 4 FAILED: Should include filename and type")
        passed = False
    
    # Test 5: Unknown function (should return empty)
    response5 = {"success": True}
    result5 = llm_playwright_execution._generate_guidance_message("unknown_function", response5)
    if result5 == "":
        print(f"✅ Test 5 PASSED: Unknown function returns empty string")
    else:
        print(f"❌ Test 5 FAILED: Unknown function should return empty string")
        passed = False
    
    print(f"\n{'='*60}")
    print(f"{'✅ ALL TESTS PASSED' if passed else '❌ SOME TESTS FAILED'}")
    print(f"{'='*60}\n")
    
    return passed


def test_track_browser_status():
    """Test browser status tracking and state updates."""
    print("\n" + "="*60)
    print("TEST: _track_browser_status()")
    print("="*60 + "\n")
    
    passed = True
    
    # Test 1: Track browser launch
    state1 = {
        'browser_launched': False,
        'browser_type': None,
        'current_url': None,
        'current_title': None,
        'browser_closed': False
    }
    response1 = {
        "success": True,
        "browser_type": "chromium",
        "headless": True,
        "viewport": "1920x1080"
    }
    llm_playwright_execution._track_browser_status("launch_browser", response1, state1)
    
    if state1['browser_launched'] and state1['browser_type'] == "chromium":
        print(f"✅ Test 1 PASSED: Browser launch tracked correctly")
    else:
        print(f"❌ Test 1 FAILED: Browser launch not tracked properly")
        passed = False
    
    # Test 2: Track navigation
    state2 = {
        'browser_launched': True,
        'browser_type': 'chromium',
        'current_url': None,
        'current_title': None,
        'browser_closed': False
    }
    response2 = {
        "success": True,
        "url": "https://example.com",
        "title": "Example Domain"
    }
    llm_playwright_execution._track_browser_status("navigate_to_url", response2, state2)
    
    if state2['current_url'] == "https://example.com" and state2['current_title'] == "Example Domain":
        print(f"✅ Test 2 PASSED: Navigation tracked correctly")
    else:
        print(f"❌ Test 2 FAILED: Navigation not tracked properly")
        passed = False
    
    # Test 3: Track browser close
    state3 = {
        'browser_launched': True,
        'browser_type': 'chromium',
        'current_url': "https://example.com",
        'current_title': "Example",
        'browser_closed': False
    }
    response3 = {
        "success": True,
        "closed": ["browser", "context", "page"]
    }
    llm_playwright_execution._track_browser_status("close_browser", response3, state3)
    
    if state3['browser_closed']:
        print(f"✅ Test 3 PASSED: Browser close tracked correctly")
    else:
        print(f"❌ Test 3 FAILED: Browser close not tracked properly")
        passed = False
    
    # Test 4: Non-tracked function doesn't modify state
    state4 = {
        'browser_launched': False,
        'browser_closed': False,
        'current_url': None,
        'current_title': None
    }
    response4 = {"success": True}
    llm_playwright_execution._track_browser_status("click_element", response4, state4)
    
    if not state4['browser_launched'] and not state4['browser_closed']:
        print(f"✅ Test 4 PASSED: Non-tracked function doesn't modify state")
    else:
        print(f"❌ Test 4 FAILED: Non-tracked function modified state")
        passed = False
    
    print(f"\n{'='*60}")
    print(f"{'✅ ALL TESTS PASSED' if passed else '❌ SOME TESTS FAILED'}")
    print(f"{'='*60}\n")
    
    return passed


def test_build_result():
    """Test result building with various states."""
    print("\n" + "="*60)
    print("TEST: _build_result()")
    print("="*60 + "\n")
    
    passed = True
    
    # Test 1: Successful execution with browser operations
    state1 = {
        'browser_launched': True,
        'browser_closed': True,
        'current_url': "https://example.com",
        'current_title': "Example Domain",
        'tools_executed': [
            {"name": "launch_browser", "success": True},
            {"name": "navigate_to_url", "success": True},
            {"name": "close_browser", "success": True}
        ]
    }
    result1 = llm_playwright_execution._build_result(
        state1, success=True, iterations=3, final_response="Task completed"
    )
    
    if (result1['success'] and 
        result1['browser_launched'] and 
        result1['browser_closed'] and
        result1['current_url'] == "https://example.com" and
        len(result1['tools_executed']) == 3):
        print(f"✅ Test 1 PASSED: Successful execution result built correctly")
    else:
        print(f"❌ Test 1 FAILED: Result structure incorrect")
        passed = False
    
    # Test 2: Failed execution with error
    state2 = {
        'browser_launched': False,
        'browser_closed': False,
        'current_url': None,
        'current_title': None,
        'tools_executed': []
    }
    result2 = llm_playwright_execution._build_result(
        state2, success=False, iterations=1, error="Connection timeout"
    )
    
    if (not result2['success'] and 
        result2['error'] == "Connection timeout" and
        not result2['browser_launched']):
        print(f"✅ Test 2 PASSED: Failed execution result built correctly")
    else:
        print(f"❌ Test 2 FAILED: Error result structure incorrect")
        passed = False
    
    # Test 3: Partial execution (browser launched but not closed)
    state3 = {
        'browser_launched': True,
        'browser_closed': False,
        'current_url': "https://example.com",
        'current_title': "Example",
        'tools_executed': [
            {"name": "launch_browser", "success": True},
            {"name": "navigate_to_url", "success": True}
        ]
    }
    result3 = llm_playwright_execution._build_result(
        state3, success=True, iterations=5
    )
    
    if (result3['browser_launched'] and 
        not result3['browser_closed'] and
        result3['iterations'] == 5):
        print(f"✅ Test 3 PASSED: Partial execution result built correctly")
    else:
        print(f"❌ Test 3 FAILED: Partial result structure incorrect")
        passed = False
    
    print(f"\n{'='*60}")
    print(f"{'✅ ALL TESTS PASSED' if passed else '❌ SOME TESTS FAILED'}")
    print(f"{'='*60}\n")
    
    return passed


# ============================================================================
# Test Tool Execution with Mocks
# ============================================================================

def test_execute_tool_success():
    """Test successful tool execution."""
    print("\n" + "="*60)
    print("TEST: _execute_tool() with successful execution")
    print("="*60 + "\n")
    
    passed = True
    
    # Mock tool call
    mock_tool_call = Mock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "launch_browser"
    mock_tool_call.function.arguments = '{"browser_type": "chromium", "headless": true}'
    
    # Mock the function
    mock_response = {
        "success": True,
        "browser_type": "chromium",
        "headless": True,
        "viewport": "1920x1080"
    }
    
    # Temporarily replace the function
    original_func = llm_playwright_execution.available_functions.get("launch_browser")
    llm_playwright_execution.available_functions["launch_browser"] = lambda **kwargs: mock_response
    
    try:
        state = {
            'browser_launched': False,
            'browser_closed': False,
            'tools_executed': []
        }
        
        result = llm_playwright_execution._execute_tool(mock_tool_call, state)
        
        # Verify result structure
        if (result is not None and
            result['tool_call_id'] == "call_123" and
            result['response']['success'] and
            result['guidance'] and
            len(state['tools_executed']) == 1):
            print(f"✅ Test PASSED: Tool execution successful")
            print(f"   Tool call ID: {result['tool_call_id']}")
            print(f"   Guidance: {result['guidance']}")
        else:
            print(f"❌ Test FAILED: Tool execution result incorrect")
            passed = False
    
    finally:
        # Restore original function
        if original_func:
            llm_playwright_execution.available_functions["launch_browser"] = original_func
    
    print(f"\n{'='*60}")
    print(f"{'✅ TEST PASSED' if passed else '❌ TEST FAILED'}")
    print(f"{'='*60}\n")
    
    return passed


def test_execute_tool_failure():
    """Test tool execution with error handling."""
    print("\n" + "="*60)
    print("TEST: _execute_tool() with error handling")
    print("="*60 + "\n")
    
    passed = True
    
    # Mock tool call
    mock_tool_call = Mock()
    mock_tool_call.id = "call_456"
    mock_tool_call.function.name = "navigate_to_url"
    mock_tool_call.function.arguments = '{"url": "https://invalid-url"}'
    
    # Mock function that raises exception
    def mock_failing_function(**kwargs):
        raise Exception("Network connection failed")
    
    # Temporarily replace the function
    original_func = llm_playwright_execution.available_functions.get("navigate_to_url")
    llm_playwright_execution.available_functions["navigate_to_url"] = mock_failing_function
    
    try:
        state = {
            'browser_launched': True,
            'browser_closed': False,
            'tools_executed': []
        }
        
        result = llm_playwright_execution._execute_tool(mock_tool_call, state)
        
        # Verify error handling
        if (result is not None and
            result['tool_call_id'] == "call_456" and
            not result['response']['success'] and
            "Network connection failed" in result['response']['error'] and
            "failed" in result['guidance'].lower()):
            print(f"✅ Test PASSED: Error handled correctly")
            print(f"   Error message: {result['response']['error']}")
            print(f"   Guidance: {result['guidance']}")
        else:
            print(f"❌ Test FAILED: Error not handled properly")
            passed = False
    
    finally:
        # Restore original function
        if original_func:
            llm_playwright_execution.available_functions["navigate_to_url"] = original_func
    
    print(f"\n{'='*60}")
    print(f"{'✅ TEST PASSED' if passed else '❌ TEST FAILED'}")
    print(f"{'='*60}\n")
    
    return passed


def test_execute_tool_unknown():
    """Test execution of unknown tool."""
    print("\n" + "="*60)
    print("TEST: _execute_tool() with unknown tool")
    print("="*60 + "\n")
    
    passed = True
    
    # Mock tool call with unknown function
    mock_tool_call = Mock()
    mock_tool_call.id = "call_789"
    mock_tool_call.function.name = "unknown_tool"
    mock_tool_call.function.arguments = '{}'
    
    state = {
        'browser_launched': False,
        'browser_closed': False,
        'tools_executed': []
    }
    
    result = llm_playwright_execution._execute_tool(mock_tool_call, state)
    
    # Should return None for unknown tool
    if result is None:
        print(f"✅ Test PASSED: Unknown tool returns None")
    else:
        print(f"❌ Test FAILED: Unknown tool should return None")
        passed = False
    
    print(f"\n{'='*60}")
    print(f"{'✅ TEST PASSED' if passed else '❌ TEST FAILED'}")
    print(f"{'='*60}\n")
    
    return passed


# ============================================================================
# Integration Tests
# ============================================================================

def test_run_with_mocked_llm():
    """Test full run() execution with mocked LLM responses."""
    print("\n" + "="*60)
    print("TEST: run() with mocked LLM")
    print("="*60 + "\n")
    
    passed = True
    
    # Mock OpenAI client
    mock_client = MagicMock()
    
    # Mock first response: LLM calls launch_browser tool
    mock_response_1 = MagicMock()
    mock_response_1.choices[0].message.content = None
    mock_response_1.choices[0].message.tool_calls = [
        MagicMock(
            id="call_1",
            function=MagicMock(
                name="launch_browser",
                arguments='{"browser_type": "chromium", "headless": true}'
            )
        )
    ]
    mock_response_1.choices[0].finish_reason = "tool_calls"
    
    # Mock second response: LLM provides final answer
    mock_response_2 = MagicMock()
    mock_response_2.choices[0].message.content = "Browser launched successfully"
    mock_response_2.choices[0].message.tool_calls = None
    mock_response_2.choices[0].finish_reason = "stop"
    
    # Set up mock to return responses in sequence
    mock_client.chat.completions.create.side_effect = [mock_response_1, mock_response_2]
    
    # Mock playwright tools
    original_launch = llm_playwright_execution.available_functions.get("launch_browser")
    llm_playwright_execution.available_functions["launch_browser"] = lambda **kwargs: {
        "success": True,
        "browser_type": "chromium",
        "headless": True,
        "viewport": "1920x1080"
    }
    
    # Replace client
    original_client = llm_playwright_execution.llm_playwright_client
    llm_playwright_execution.llm_playwright_client = mock_client
    
    try:
        result = llm_playwright_execution.run("Launch a browser")
        
        if (result['success'] and
            result['browser_launched'] and
            result['iterations'] == 2 and
            "Browser launched successfully" in result.get('final_response', '')):
            print(f"✅ Test PASSED: Full execution with mocked LLM")
            print(f"   Success: {result['success']}")
            print(f"   Browser launched: {result['browser_launched']}")
            print(f"   Iterations: {result['iterations']}")
            print(f"   Tools executed: {len(result['tools_executed'])}")
        else:
            print(f"❌ Test FAILED: Execution result incorrect")
            print(f"   Result: {json.dumps(result, indent=2)}")
            passed = False
    
    except Exception as e:
        print(f"❌ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        passed = False
    
    finally:
        # Restore originals
        llm_playwright_execution.llm_playwright_client = original_client
        if original_launch:
            llm_playwright_execution.available_functions["launch_browser"] = original_launch
    
    print(f"\n{'='*60}")
    print(f"{'✅ TEST PASSED' if passed else '❌ TEST FAILED'}")
    print(f"{'='*60}\n")
    
    return passed


def test_run_max_iterations():
    """Test that run() respects max_iterations limit."""
    print("\n" + "="*60)
    print("TEST: run() with max iterations")
    print("="*60 + "\n")
    
    passed = True
    
    # Mock OpenAI client that always calls tools (infinite loop)
    mock_client = MagicMock()
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.tool_calls = [
        MagicMock(
            id="call_loop",
            function=MagicMock(
                name="get_page_info",
                arguments='{}'
            )
        )
    ]
    mock_response.choices[0].finish_reason = "tool_calls"
    
    # Always return same response (infinite loop)
    mock_client.chat.completions.create.return_value = mock_response
    
    # Mock get_page_info
    original_func = llm_playwright_execution.available_functions.get("get_page_info")
    llm_playwright_execution.available_functions["get_page_info"] = lambda **kwargs: {
        "success": True,
        "url": "https://test.com",
        "title": "Test"
    }
    
    # Replace client
    original_client = llm_playwright_execution.llm_playwright_client
    llm_playwright_execution.llm_playwright_client = mock_client
    
    try:
        # Run with default max_iterations=15
        result = llm_playwright_execution.run("Test infinite loop")
        
        if result['iterations'] == 15:
            print(f"✅ Test PASSED: Max iterations respected")
            print(f"   Iterations: {result['iterations']}")
            print(f"   Tools executed: {len(result['tools_executed'])}")
        else:
            print(f"❌ Test FAILED: Should stop at max_iterations=15")
            print(f"   Iterations: {result['iterations']}")
            passed = False
    
    except Exception as e:
        print(f"❌ Test FAILED with exception: {str(e)}")
        passed = False
    
    finally:
        # Restore originals
        llm_playwright_execution.llm_playwright_client = original_client
        if original_func:
            llm_playwright_execution.available_functions["get_page_info"] = original_func
    
    print(f"\n{'='*60}")
    print(f"{'✅ TEST PASSED' if passed else '❌ TEST FAILED'}")
    print(f"{'='*60}\n")
    
    return passed


# ============================================================================
# Main Test Runner
# ============================================================================

def run_all_tests():
    """Run all test suites."""
    print("\n" + "="*60)
    print("COMPREHENSIVE TEST SUITE FOR llm_playwright_execution.py")
    print("="*60)
    
    results = []
    
    # Helper function tests
    print("\n" + "─"*60)
    print("HELPER FUNCTIONS TESTS")
    print("─"*60)
    results.append(("_get_extraction_guidance", test_get_extraction_guidance()))
    results.append(("_generate_guidance_message", test_generate_guidance_message()))
    results.append(("_track_browser_status", test_track_browser_status()))
    results.append(("_build_result", test_build_result()))
    
    # Tool execution tests
    print("\n" + "─"*60)
    print("TOOL EXECUTION TESTS")
    print("─"*60)
    results.append(("_execute_tool (success)", test_execute_tool_success()))
    results.append(("_execute_tool (failure)", test_execute_tool_failure()))
    results.append(("_execute_tool (unknown)", test_execute_tool_unknown()))
    
    # Integration tests
    print("\n" + "─"*60)
    print("INTEGRATION TESTS")
    print("─"*60)
    results.append(("run() with mocked LLM", test_run_with_mocked_llm()))
    results.append(("run() max iterations", test_run_max_iterations()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<50} {status}")
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {total_count - passed_count} TEST(S) FAILED")
    
    print("="*60 + "\n")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
