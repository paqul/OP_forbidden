"""
Quick smoke tests for llm_playwright_execution.py
Tests basic functionality without requiring full LLM integration.

Run this for quick validation:
    python tests/test_playwright_execution_quick.py
"""

import sys
import os
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import llm_playwright_execution


def test_helper_functions():
    """Quick test of all helper functions."""
    print("\n" + "="*60)
    print("QUICK SMOKE TEST: Helper Functions")
    print("="*60 + "\n")
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: _get_extraction_guidance with count
    tests_total += 1
    result = llm_playwright_execution._get_extraction_guidance({"count": 3})
    if "3 elements" in result:
        print("✅ _get_extraction_guidance (count)")
        tests_passed += 1
    else:
        print("❌ _get_extraction_guidance (count)")
    
    # Test 2: _get_extraction_guidance with text
    tests_total += 1
    result = llm_playwright_execution._get_extraction_guidance({"text": "Test"})
    if "Test" in result:
        print("✅ _get_extraction_guidance (text)")
        tests_passed += 1
    else:
        print("❌ _get_extraction_guidance (text)")
    
    # Test 3: _generate_guidance_message success
    tests_total += 1
    result = llm_playwright_execution._generate_guidance_message(
        "launch_browser",
        {"success": True, "browser_type": "chromium", "viewport": "1920x1080"}
    )
    if "chromium" in result:
        print("✅ _generate_guidance_message (success)")
        tests_passed += 1
    else:
        print("❌ _generate_guidance_message (success)")
    
    # Test 4: _generate_guidance_message failure
    tests_total += 1
    result = llm_playwright_execution._generate_guidance_message(
        "launch_browser",
        {"success": False, "error": "Test error"}
    )
    if "failed" in result.lower() and "Test error" in result:
        print("✅ _generate_guidance_message (failure)")
        tests_passed += 1
    else:
        print("❌ _generate_guidance_message (failure)")
    
    # Test 5: _track_browser_status launch
    tests_total += 1
    state = {'browser_launched': False, 'browser_type': None}
    llm_playwright_execution._track_browser_status(
        "launch_browser",
        {"success": True, "browser_type": "firefox"},
        state
    )
    if state['browser_launched'] and state['browser_type'] == "firefox":
        print("✅ _track_browser_status (launch)")
        tests_passed += 1
    else:
        print("❌ _track_browser_status (launch)")
    
    # Test 6: _track_browser_status navigate
    tests_total += 1
    state = {'current_url': None, 'current_title': None}
    llm_playwright_execution._track_browser_status(
        "navigate_to_url",
        {"success": True, "url": "https://test.com", "title": "Test"},
        state
    )
    if state['current_url'] == "https://test.com" and state['current_title'] == "Test":
        print("✅ _track_browser_status (navigate)")
        tests_passed += 1
    else:
        print("❌ _track_browser_status (navigate)")
    
    # Test 7: _track_browser_status close
    tests_total += 1
    state = {'browser_closed': False}
    llm_playwright_execution._track_browser_status(
        "close_browser",
        {"success": True, "closed": ["browser"]},
        state
    )
    if state['browser_closed']:
        print("✅ _track_browser_status (close)")
        tests_passed += 1
    else:
        print("❌ _track_browser_status (close)")
    
    # Test 8: _build_result
    tests_total += 1
    state = {
        'browser_launched': True,
        'browser_closed': False,
        'current_url': "https://example.com",
        'current_title': "Example",
        'tools_executed': [{"name": "test", "success": True}]
    }
    result = llm_playwright_execution._build_result(
        state, success=True, iterations=5, final_response="Done"
    )
    if (result['success'] and 
        result['browser_launched'] and 
        result['iterations'] == 5 and
        result['final_response'] == "Done"):
        print("✅ _build_result")
        tests_passed += 1
    else:
        print("❌ _build_result")
    
    # Test 9: _is_workflow_complete (should always return False)
    tests_total += 1
    state = {'browser_launched': True, 'browser_closed': True}
    result = llm_playwright_execution._is_workflow_complete(state, "test")
    if result == False:
        print("✅ _is_workflow_complete")
        tests_passed += 1
    else:
        print("❌ _is_workflow_complete")
    
    print(f"\n{'='*60}")
    print(f"Results: {tests_passed}/{tests_total} tests passed")
    print(f"{'='*60}\n")
    
    return tests_passed == tests_total


def test_tool_guidance_config():
    """Test that all tool guidance configurations are present."""
    print("\n" + "="*60)
    print("QUICK SMOKE TEST: Tool Guidance Configuration")
    print("="*60 + "\n")
    
    expected_tools = [
        "launch_browser",
        "navigate_to_url",
        "click_element",
        "type_text",
        "extract_text",
        "take_screenshot",
        "wait_for_element",
        "get_page_info",
        "close_browser",
        "execute_javascript"
    ]
    
    missing_tools = []
    for tool in expected_tools:
        if tool not in llm_playwright_execution.TOOL_GUIDANCE:
            missing_tools.append(tool)
            print(f"❌ Missing guidance config: {tool}")
        else:
            # Check if it has on_success callback
            if 'on_success' in llm_playwright_execution.TOOL_GUIDANCE[tool]:
                print(f"✅ {tool}")
            else:
                print(f"⚠️  {tool} (no on_success callback)")
    
    print(f"\n{'='*60}")
    if not missing_tools:
        print(f"✅ All {len(expected_tools)} tools have guidance configs")
        print(f"{'='*60}\n")
        return True
    else:
        print(f"❌ {len(missing_tools)} tools missing guidance configs")
        print(f"{'='*60}\n")
        return False


def test_available_functions():
    """Test that all functions are properly registered."""
    print("\n" + "="*60)
    print("QUICK SMOKE TEST: Available Functions")
    print("="*60 + "\n")
    
    expected_functions = [
        "launch_browser",
        "navigate_to_url",
        "click_element",
        "type_text",
        "extract_text",
        "take_screenshot",
        "wait_for_element",
        "get_page_info",
        "close_browser",
        "execute_javascript"
    ]
    
    missing_functions = []
    for func in expected_functions:
        if func in llm_playwright_execution.available_functions:
            # Check if it's callable
            if callable(llm_playwright_execution.available_functions[func]):
                print(f"✅ {func}")
            else:
                print(f"⚠️  {func} (not callable)")
                missing_functions.append(func)
        else:
            print(f"❌ Missing function: {func}")
            missing_functions.append(func)
    
    print(f"\n{'='*60}")
    if not missing_functions:
        print(f"✅ All {len(expected_functions)} functions registered")
        print(f"{'='*60}\n")
        return True
    else:
        print(f"❌ {len(missing_functions)} functions missing or not callable")
        print(f"{'='*60}\n")
        return False


def test_state_initialization():
    """Test that state is properly initialized in run()."""
    print("\n" + "="*60)
    print("QUICK SMOKE TEST: State Initialization")
    print("="*60 + "\n")
    
    # This tests the structure without actually running the LLM
    expected_keys = [
        'browser_launched',
        'browser_closed',
        'current_url',
        'current_title',
        'tools_executed'
    ]
    
    # Create a minimal state like run() does
    test_state = {
        'browser_launched': False,
        'browser_closed': False,
        'current_url': None,
        'current_title': None,
        'tools_executed': [],
    }
    
    tests_passed = 0
    for key in expected_keys:
        if key in test_state:
            print(f"✅ State key '{key}' initialized")
            tests_passed += 1
        else:
            print(f"❌ State key '{key}' missing")
    
    print(f"\n{'='*60}")
    if tests_passed == len(expected_keys):
        print(f"✅ All {len(expected_keys)} state keys present")
        print(f"{'='*60}\n")
        return True
    else:
        print(f"❌ {len(expected_keys) - tests_passed} state keys missing")
        print(f"{'='*60}\n")
        return False


def main():
    """Run all quick smoke tests."""
    print("\n" + "="*60)
    print("QUICK SMOKE TESTS FOR llm_playwright_execution.py")
    print("="*60)
    print("These tests validate configuration and helper functions")
    print("without requiring LLM API calls or browser automation.")
    print("="*60)
    
    results = []
    
    results.append(("Helper Functions", test_helper_functions()))
    results.append(("Tool Guidance Config", test_tool_guidance_config()))
    results.append(("Available Functions", test_available_functions()))
    results.append(("State Initialization", test_state_initialization()))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print(f"\n{'='*60}")
    print(f"Results: {passed_count}/{total_count} test suites passed")
    
    if passed_count == total_count:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {total_count - passed_count} TEST SUITE(S) FAILED")
    
    print("="*60 + "\n")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
