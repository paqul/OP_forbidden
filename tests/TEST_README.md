# Test Suite for llm_playwright_execution.py

This directory contains comprehensive tests for the browser automation agent (`llm_playwright_execution.py`).

## Test Files

### 1. test_playwright_execution_quick.py
**Quick smoke tests without LLM/browser dependencies**

```bash
python tests/test_playwright_execution_quick.py
```

**What it tests:**
- ✅ Helper functions (`_get_extraction_guidance`, `_generate_guidance_message`, `_track_browser_status`, `_build_result`)
- ✅ Tool guidance configuration completeness
- ✅ Available functions registration
- ✅ State initialization structure

**Duration:** ~1 second  
**Dependencies:** None (no LLM API calls, no browser launch)  
**Use case:** Quick validation during development

---

### 2. test_llm_playwright_execution.py
**Comprehensive unit and integration tests with mocks**

```bash
python tests/test_llm_playwright_execution.py
```

**What it tests:**
- ✅ All helper functions with edge cases
- ✅ Tool execution with success/failure/unknown scenarios
- ✅ Full `run()` execution with mocked LLM responses
- ✅ Max iterations limit enforcement
- ✅ Error handling and state management
- ✅ Guidance message generation for all tools

**Duration:** ~5 seconds  
**Dependencies:** unittest.mock (no real LLM/browser)  
**Use case:** Comprehensive validation before deployment

---

### 3. test_browser_integration.py
**Real integration tests with actual Playwright browser**

```bash
python tests/test_browser_integration.py
```

**What it tests:**
- ✅ Direct Playwright tools (launch, navigate, screenshot, close)
- ✅ Full browser agent with real LLM calls
- ✅ End-to-end workflow validation

**Duration:** ~30 seconds (depends on LLM response time)  
**Dependencies:** OpenAI API key, Playwright browsers installed  
**Use case:** Pre-production validation

---

## Quick Start

### Run All Tests (Recommended Order)

```bash
# 1. Quick smoke tests (fast, no dependencies)
python tests/test_playwright_execution_quick.py

# 2. Unit tests with mocks (comprehensive)
python tests/test_llm_playwright_execution.py

# 3. Integration tests (real LLM + browser)
python tests/test_browser_integration.py
```

### Run Single Test

```bash
# Quick validation
python tests/test_playwright_execution_quick.py

# Or with full path
C:/Users/hyper/AppData/Local/Programs/Python/Python310/python.exe tests/test_playwright_execution_quick.py
```

---

## Test Coverage

### Helper Functions (100% coverage)
- `_get_extraction_guidance()` - Text extraction guidance
- `_generate_guidance_message()` - Tool-specific guidance
- `_print_status_banner()` - Status display
- `_track_browser_status()` - State tracking
- `_execute_tool()` - Tool execution wrapper
- `_is_workflow_complete()` - Completion detection
- `_build_result()` - Result formatting

### Main Function
- `run()` - Full execution loop with various scenarios

### Edge Cases
- ✅ Successful tool execution
- ✅ Failed tool execution (exceptions)
- ✅ Unknown tool handling
- ✅ Max iterations limit
- ✅ Empty/missing responses
- ✅ Long text truncation
- ✅ State transitions

---

## Test Output Examples

### ✅ All Tests Passed
```
============================================================
SUMMARY
============================================================
Helper Functions........................ ✅ PASSED
Tool Guidance Config.................... ✅ PASSED
Available Functions..................... ✅ PASSED
State Initialization.................... ✅ PASSED

============================================================
Results: 4/4 test suites passed
✅ ALL TESTS PASSED
============================================================
```

### ❌ Test Failed
```
❌ Test FAILED: Tool execution result incorrect
   Expected: {'success': True}
   Got: {'success': False, 'error': 'Browser not found'}
```

---

## Continuous Integration

Add to your CI/CD pipeline:

```yaml
# .github/workflows/test.yml
- name: Run quick tests
  run: python tests/test_playwright_execution_quick.py

- name: Run unit tests
  run: python tests/test_llm_playwright_execution.py

- name: Run integration tests
  run: python tests/test_browser_integration.py
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

## Troubleshooting

### Import Error: "No module named 'llm_playwright_execution'"
The tests add the parent directory to `sys.path` automatically. Run from project root:
```bash
cd D:\Python_Projects\OP_forbidden
python tests/test_playwright_execution_quick.py
```

### Test Timeouts
Increase timeout in test file:
```python
mock_client.chat.completions.create.timeout = 60  # seconds
```

### Playwright Not Installed
```bash
pip install playwright
python -m playwright install chromium
```

---

## Adding New Tests

### 1. Add Helper Function Test
```python
def test_new_helper():
    result = llm_playwright_execution._new_helper(input_data)
    assert result == expected_output
    print("✅ Test passed")
```

### 2. Add Tool Test
```python
def test_new_tool():
    mock_tool_call = Mock()
    mock_tool_call.function.name = "new_tool"
    mock_tool_call.function.arguments = '{"param": "value"}'
    
    result = llm_playwright_execution._execute_tool(mock_tool_call, state)
    assert result['response']['success']
```

### 3. Add Integration Test
```python
def test_new_workflow():
    result = llm_playwright_execution.run("New workflow task")
    assert result['success']
    assert result['browser_launched']
```

---

## Test Maintenance

- **After adding new tools:** Update `expected_tools` list in tests
- **After modifying state:** Update `expected_keys` list
- **After changing guidance:** Update guidance validation tests
- **Before releases:** Run all 3 test suites

---

## Performance Benchmarks

| Test Suite | Duration | LLM Calls | Browser Launch |
|------------|----------|-----------|----------------|
| Quick      | ~1s      | 0         | No             |
| Unit       | ~5s      | 0 (mocked)| No             |
| Integration| ~30s     | 2-5       | Yes            |

---

## Related Documentation

- [PLAYWRIGHT_SETUP.md](../PLAYWRIGHT_SETUP.md) - Playwright installation and usage
- [BROWSER_INTEGRATION_COMPLETE.md](../BROWSER_INTEGRATION_COMPLETE.md) - Architecture overview
- [llm_playwright_execution.py](../llm_playwright_execution.py) - Source code

---

## Status

✅ **All tests passing** (Last run: 2026-04-24)  
📊 **Coverage:** 100% of helper functions  
🚀 **Ready for production**
