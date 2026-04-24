# Playwright Browser Automation Setup

## Installation

### 1. Install Playwright Python Package
```powershell
pip install playwright
```

### 2. Install Browser Binaries
After installing the Python package, you need to install the browser binaries:

```powershell
playwright install chromium
```

Or install all browsers:
```powershell
playwright install
```

This downloads Chromium, Firefox, and WebKit browsers that Playwright controls.

## Quick Start

### Launch Browser and Navigate
```python
import playwright_tools

# Launch browser (visible window by default)
result = playwright_tools.launch_browser(browser_type="chromium", headless=False)
print(result)

# Navigate to a website
result = playwright_tools.navigate_to_url("https://www.example.com")
print(result)

# Get page info
result = playwright_tools.get_page_info()
print(result)

# Close browser
result = playwright_tools.close_browser()
print(result)
```

### Extract Data from Website
```python
# Launch browser
playwright_tools.launch_browser()

# Navigate to target
playwright_tools.navigate_to_url("https://news.ycombinator.com")

# Extract all article titles
result = playwright_tools.extract_text(".titleline > a", extract_all=True)
print(f"Found {result['count']} articles")
for text in result['texts']:
    print(f"- {text}")

# Take screenshot
playwright_tools.take_screenshot("hackernews_homepage")

# Close when done
playwright_tools.close_browser()
```

### Interact with Forms
```python
# Launch browser in headed mode to see what's happening
playwright_tools.launch_browser(headless=False)

# Navigate to search page
playwright_tools.navigate_to_url("https://www.google.com")

# Wait for search box
playwright_tools.wait_for_element("textarea[name='q']")

# Type search query
playwright_tools.type_text("textarea[name='q']", "Playwright automation", press_enter=True)

# Wait for results
playwright_tools.wait_for_element("#search")

# Extract search results
results = playwright_tools.extract_text("h3", extract_all=True)
print(results)
```

## Available Tools

### Browser Management
- **launch_browser()** - Launch Chromium/Firefox/WebKit browser
- **close_browser()** - Close browser and cleanup
- **get_page_info()** - Get current page title, URL, viewport

### Navigation
- **navigate_to_url(url)** - Go to a website
- **wait_for_element(selector, state)** - Wait for element to appear/disappear

### Interaction
- **click_element(selector)** - Click on buttons, links, etc.
- **type_text(selector, text)** - Type into input fields
- **execute_javascript(script)** - Run custom JavaScript

### Data Extraction
- **extract_text(selector, extract_all)** - Extract text from elements
- **take_screenshot(filename, full_page)** - Capture page as PNG

## Selector Types

### CSS Selectors
```python
"div.classname"           # Element with class
"#id"                     # Element with ID
"button[type='submit']"   # Element with attribute
"ul > li"                 # Direct children
```

### Text Selectors
```python
"text='Click Here'"       # Exact text match
"text=/pattern/"          # Regex pattern
```

### Role-based Selectors (Accessible)
```python
"role=button[name='Submit']"
"role=link[name='Learn more']"
```

## Common Workflows

### 1. Web Scraping
```python
# Launch → Navigate → Extract → Close
launch_browser()
navigate_to_url("https://example.com/products")
products = extract_text(".product-title", extract_all=True)
close_browser()
```

### 2. Form Automation
```python
# Launch → Navigate → Fill form → Submit
launch_browser()
navigate_to_url("https://example.com/login")
type_text("#username", "myuser")
type_text("#password", "mypass")
click_element("button[type='submit']")
```

### 3. Screenshot Monitoring
```python
# Launch → Navigate → Screenshot → Close
launch_browser()
navigate_to_url("https://example.com")
take_screenshot("site_monitoring", full_page=True)
close_browser()
```

## Integration with LLM Orchestrator

The Playwright tools are integrated with the main orchestrator:

```python
# Ask orchestrator to use browser agent
user_message = "Navigate to YouTube and take a screenshot of the homepage"

# Orchestrator will automatically:
# 1. Recognize this is a browser task
# 2. Call browser agent (llm_playwright_execution)
# 3. Browser agent executes Playwright tools
# 4. Returns results to orchestrator
```

## File Locations

- **playwright_tools.py** - Core Playwright functions (10 tools)
- **llm_playwright_execution.py** - LLM agent for browser automation
- **screenshots/** - Saved screenshots (auto-created)
- **scraped_data/** - Extracted data (auto-created)

## Error Handling

All tools return JSON with success status:

```python
{
    "success": True/False,
    "error": "Error message if failed",
    ... additional data ...
}
```

Always check `success` field before using results.

## Best Practices

1. **Launch once, use multiple times** - Browser persists between tasks
2. **Use wait_for_element** - Before clicking dynamic content
3. **Descriptive filenames** - For screenshots and data files
4. **Close when done** - Cleanup resources with close_browser()
5. **Headed mode for debugging** - See what's happening (headless=False)

## Troubleshooting

**Module not found error:**
```powershell
pip install playwright
playwright install chromium
```

**Browser not launching:**
- Check if running as administrator (may be needed)
- Verify Playwright browsers are installed: `playwright install`

**Element not found:**
- Use wait_for_element before interaction
- Verify selector with browser DevTools (F12)
- Try different selector types (CSS, text, role)

**Timeout errors:**
- Increase timeout parameter (default: 30000ms)
- Check if page needs more time to load
- Use wait_until="networkidle" for slow pages
