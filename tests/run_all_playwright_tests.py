"""
Master test runner for llm_playwright_execution.py
Runs all test suites in sequence and provides consolidated results.

Usage:
    python tests/run_all_playwright_tests.py
    
Or with PowerShell:
    C:/Users/hyper/AppData/Local/Programs/Python/Python310/python.exe tests/run_all_playwright_tests.py
"""

import sys
import os
import subprocess
import time
from datetime import datetime

# Test files to run (in order)
TEST_FILES = [
    ("Quick Smoke Tests", "tests/test_playwright_execution_quick.py"),
    ("Unit Tests (Mocked)", "tests/test_llm_playwright_execution.py"),
]

# Optional integration test (requires LLM API and browser)
INTEGRATION_TEST = ("Integration Test (Real LLM/Browser)", "tests/test_browser_integration.py")


def print_banner(text, char="="):
    """Print a formatted banner."""
    width = 70
    print("\n" + char * width)
    print(f" {text}")
    print(char * width + "\n")


def run_test(test_name, test_file):
    """Run a single test file and return success status."""
    print_banner(f"Running: {test_name}")
    print(f"File: {test_file}")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}\n")
    
    start_time = time.time()
    
    try:
        # Run the test
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        duration = time.time() - start_time
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:", result.stderr)
        
        # Check success
        success = result.returncode == 0
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"\n{status} - Duration: {duration:.2f}s")
        print(f"Finished: {datetime.now().strftime('%H:%M:%S')}")
        
        return {
            "name": test_name,
            "success": success,
            "duration": duration,
            "returncode": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"\n❌ TIMEOUT - Test exceeded 60 seconds")
        return {
            "name": test_name,
            "success": False,
            "duration": duration,
            "returncode": -1,
            "error": "Timeout"
        }
    
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ ERROR: {str(e)}")
        return {
            "name": test_name,
            "success": False,
            "duration": duration,
            "returncode": -1,
            "error": str(e)
        }


def main():
    """Run all test suites and display results."""
    print_banner("PLAYWRIGHT AGENT TEST SUITE", "=")
    print(f"Python: {sys.version}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Run core tests
    for test_name, test_file in TEST_FILES:
        result = run_test(test_name, test_file)
        results.append(result)
        
        # If a test fails, ask if user wants to continue
        if not result['success']:
            print("\n⚠️  Test failed. Continue with remaining tests? (y/n): ", end="")
            # Auto-continue in CI environments
            if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                print("yes (CI mode)")
            else:
                # In interactive mode, continue anyway for complete report
                print("yes (auto-continue)")
    
    # Ask about integration test
    print_banner("Integration Test Option")
    print("The integration test requires:")
    print("  - OpenAI API key configured")
    print("  - Playwright browsers installed")
    print("  - ~30-60 seconds to complete")
    print("\nRun integration test? (y/n): ", end="")
    
    # Auto-skip in non-interactive or if previous tests failed
    run_integration = False
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        print("no (CI mode)")
    else:
        # Auto-run if all previous tests passed
        if all(r['success'] for r in results):
            print("yes (auto-run, all tests passed)")
            run_integration = True
        else:
            print("no (skipped, previous tests failed)")
    
    if run_integration:
        result = run_test(INTEGRATION_TEST[0], INTEGRATION_TEST[1])
        results.append(result)
    
    # Print summary
    print_banner("TEST RESULTS SUMMARY", "=")
    
    total_duration = sum(r['duration'] for r in results)
    passed_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    
    print(f"{'Test Suite':<45} {'Status':<10} {'Duration'}")
    print("-" * 70)
    
    for result in results:
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        duration = f"{result['duration']:.2f}s"
        print(f"{result['name']:<45} {status:<10} {duration}")
    
    print("-" * 70)
    print(f"{'TOTAL':<45} {passed_count}/{total_count} {'':>10} {total_duration:.2f}s")
    
    print(f"\n{'='*70}")
    if passed_count == total_count:
        print("✅ ALL TESTS PASSED")
        print(f"{'='*70}\n")
        return 0
    else:
        print(f"❌ {total_count - passed_count} TEST SUITE(S) FAILED")
        print(f"{'='*70}\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
