"""
Test script to verify browser agent integration with orchestrator.
This test launches browser, navigates to example.com, and takes a screenshot.
"""

import playwright_tools
import llm_playwright_execution
from logger.logger_file import log_session_summary


def test_playwright_tools_direct():
    """Test Playwright tools directly without LLM."""
    print("\n" + "="*60)
    print("TEST 1: Direct Playwright Tools Test")
    print("="*60 + "\n")
    
    try:
        # Launch browser (visible window)
        print("1. Launching browser...")
        result = playwright_tools.launch_browser(browser_type="webkit", headless=False)
        print(f"   ✅ Browser launched: {result['success']}")
        
        # Navigate to example.com
        print("\n2. Navigating to example.com...")
        result = playwright_tools.navigate_to_url("https://www.example.com")
        print(f"   ✅ Navigation successful: {result['success']}")
        print(f"   URL: {result['current_url']}")
        print(f"   Title: {result['title']}")
        
        # Get page info
        print("\n3. Getting page info...")
        result = playwright_tools.get_page_info()
        print(f"   ✅ Page info retrieved")
        print(f"   Title: {result['title']}")
        print(f"   URL: {result['url']}")
        
        # Take screenshot
        print("\n4. Taking screenshot...")
        result = playwright_tools.take_screenshot("test_example_com", full_page=True)
        print(f"   ✅ Screenshot saved: {result['file_path']}")
        
        # Close browser
        print("\n5. Closing browser...")
        result = playwright_tools.close_browser()
        print(f"   ✅ Browser closed: {result['success']}")
        
        print("\n" + "="*60)
        print("✅ TEST 1 PASSED: All Playwright tools working correctly")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {str(e)}")
        return False


def test_browser_agent():
    """Test browser agent LLM execution."""
    print("\n" + "="*60)
    print("TEST 2: Browser Agent LLM Test")
    print("="*60 + "\n")
    
    try:
        user_message = "Launch a browser, navigate to example.com, and take a screenshot"
        
        print(f"User Task: {user_message}")
        print("\nExecuting browser agent...\n")
        
        result = llm_playwright_execution.run(user_message)
        
        print("\n" + "-"*60)
        print("Browser Agent Result:")
        print("-"*60)
        print(f"Success: {result.get('success')}")
        print(f"Browser Launched: {result.get('browser_launched')}")
        print(f"Current URL: {result.get('current_url')}")
        print(f"Current Title: {result.get('current_title')}")
        print(f"Final Message: {result.get('message', '')}")
        
        if result.get('success'):
            print("\n" + "="*60)
            print("✅ TEST 2 PASSED: Browser agent executed successfully")
            print("="*60 + "\n")
            return True
        else:
            print("\n" + "="*60)
            print("❌ TEST 2 FAILED: Browser agent returned success=False")
            print("="*60 + "\n")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("BROWSER INTEGRATION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Direct tools
    results.append(("Direct Playwright Tools", test_playwright_tools_direct()))
    
    # Test 2: Browser agent with LLM
    results.append(("Browser Agent LLM", test_browser_agent()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    main()
