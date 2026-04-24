import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

# Screenshot and data storage paths
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCRAPED_DATA_DIR = Path(__file__).parent / "scraped_data"

# Ensure directories exist
SCREENSHOTS_DIR.mkdir(exist_ok=True)
SCRAPED_DATA_DIR.mkdir(exist_ok=True)

# Global browser state
_browser_instance = None
_context_instance = None
_page_instance = None
_playwright_instance = None


tools = [
    {
        "type": "function",
        "function": {
            "name": "launch_browser",
            "description": "Launch a browser instance with Playwright. Supports Chrome, Firefox, and WebKit. Can run in headless or headed mode. Returns JSON with browser launch status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "browser_type": {
                        "type": "string",
                        "description": "Type of browser to launch",
                        "enum": ["chromium", "firefox", "webkit"]
                    },
                    "headless": {
                        "type": "boolean",
                        "description": "Run browser in headless mode (no GUI). Default: True for automation, False to see browser."
                    },
                    "viewport_width": {
                        "type": "integer",
                        "description": "Browser viewport width in pixels (default: 1920)"
                    },
                    "viewport_height": {
                        "type": "integer",
                        "description": "Browser viewport height in pixels (default: 1080)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "navigate_to_url",
            "description": "Navigate browser to a specific URL. Waits for page to load. Use after launch_browser. Returns JSON with navigation status and page title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL to navigate to (e.g., 'https://www.example.com')"
                    },
                    "wait_until": {
                        "type": "string",
                        "description": "When to consider navigation successful",
                        "enum": ["load", "domcontentloaded", "networkidle"]
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum time to wait in milliseconds (default: 30000)"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_element",
            "description": "Click on an element on the page. Can use CSS selectors, text content, or accessibility labels. Returns JSON with click status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector, text selector (text='...'), or role selector (role=button[name='...'])"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum time to wait for element in milliseconds (default: 30000)"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force click even if element is not visible (default: False)"
                    }
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text into an input field or text area. Can clear existing text first. Returns JSON with typing status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for the input field"
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to type into the field"
                    },
                    "clear_first": {
                        "type": "boolean",
                        "description": "Clear existing text before typing (default: True)"
                    },
                    "press_enter": {
                        "type": "boolean",
                        "description": "Press Enter key after typing (default: False)"
                    }
                },
                "required": ["selector", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_text",
            "description": "Extract text content from one or multiple elements on the page. Returns JSON with extracted text data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for element(s) to extract text from"
                    },
                    "extract_all": {
                        "type": "boolean",
                        "description": "Extract from all matching elements (True) or just first one (False). Default: False"
                    }
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot of the current page or a specific element. Saves to screenshots/ folder. Returns JSON with screenshot path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename for screenshot (without extension, .png will be added)"
                    },
                    "full_page": {
                        "type": "boolean",
                        "description": "Capture full scrollable page (True) or just viewport (False). Default: False"
                    },
                    "selector": {
                        "type": "string",
                        "description": "CSS selector to screenshot specific element instead of whole page"
                    }
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wait_for_element",
            "description": "Wait for an element to appear on the page before proceeding. Useful before clicking or extracting. Returns JSON with wait status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for element to wait for"
                    },
                    "state": {
                        "type": "string",
                        "description": "State to wait for",
                        "enum": ["attached", "detached", "visible", "hidden"]
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum time to wait in milliseconds (default: 30000)"
                    }
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_info",
            "description": "Get current page information including title, URL, and viewport size. Returns JSON with page details.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_browser",
            "description": "Close the browser instance and cleanup resources. Should be called when automation is complete. Returns JSON with close status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Force close even if there are unsaved changes (default: True)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_javascript",
            "description": "Execute custom JavaScript code in the browser context. Returns the result of the JavaScript execution. Use for advanced interactions not covered by other tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "JavaScript code to execute"
                    },
                    "args": {
                        "type": "array",
                        "description": "Optional arguments to pass to the script",
                        "items": {"type": "string"}
                    }
                },
                "required": ["script"]
            }
        }
    }
]


def _ensure_browser_running() -> tuple:
    """Ensure browser is launched and return (success, error_message)."""
    global _browser_instance, _context_instance, _page_instance
    
    if not _playwright_instance or not _browser_instance or not _page_instance:
        return False, "Browser not launched. Call launch_browser first."
    
    try:
        # Test if page is still alive
        _page_instance.title()
        return True, None
    except Exception as e:
        return False, f"Browser connection lost: {str(e)}"


def launch_browser(browser_type: str = "webkit", headless: bool = False, 
                   viewport_width: int = 1920, viewport_height: int = 1080) -> Dict:
    """
    Launch a browser instance with Playwright.
    Supports chromium (Chrome), firefox, and webkit (Safari).
    """
    global _playwright_instance, _browser_instance, _context_instance, _page_instance
    
    try:
        # Close existing browser if any
        if _browser_instance:
            try:
                close_browser(force=True)
            except:
                pass
        
        # Launch Playwright
        _playwright_instance = sync_playwright().start()
        
        # Select browser type
        if browser_type == "chromium":
            browser = _playwright_instance.chromium
        elif browser_type == "firefox":
            browser = _playwright_instance.firefox
        elif browser_type == "webkit":
            browser = _playwright_instance.webkit
        else:
            return {
                "success": False,
                "error": f"Invalid browser type: {browser_type}. Use 'chromium', 'firefox', or 'webkit'"
            }
        
        # Launch browser
        _browser_instance = browser.launch(headless=headless)
        
        # Create browser context with viewport
        _context_instance = _browser_instance.new_context(
            viewport={"width": viewport_width, "height": viewport_height}
        )
        
        # Create new page
        _page_instance = _context_instance.new_page()
        
        return {
            "success": True,
            "browser_type": browser_type,
            "headless": headless,
            "viewport": f"{viewport_width}x{viewport_height}",
            "message": f"Browser launched successfully in {'headless' if headless else 'headed'} mode"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to launch browser: {str(e)}"
        }


def navigate_to_url(url: str, wait_until: str = "load", timeout: int = 30000) -> Dict:
    """
    Navigate to a URL and wait for page to load.
    """
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        response = _page_instance.goto(url, wait_until=wait_until, timeout=timeout)
        
        # Get page information
        title = _page_instance.title()
        current_url = _page_instance.url
        
        return {
            "success": True,
            "url": current_url,
            "title": title,
            "status": response.status if response else None,
            "message": f"Successfully navigated to {url}"
        }
        
    except PlaywrightTimeoutError:
        return {
            "success": False,
            "error": f"Navigation timeout after {timeout}ms. Page took too long to load."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Navigation failed: {str(e)}"
        }


def click_element(selector: str, timeout: int = 30000, force: bool = False) -> Dict:
    """
    Click on an element using CSS selector, text, or role.
    """
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        _page_instance.click(selector, timeout=timeout, force=force)
        
        return {
            "success": True,
            "selector": selector,
            "message": f"Successfully clicked element: {selector}"
        }
        
    except PlaywrightTimeoutError:
        return {
            "success": False,
            "error": f"Element not found or not clickable: {selector} (timeout: {timeout}ms)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Click failed: {str(e)}"
        }


def type_text(selector: str, text: str, clear_first: bool = True, press_enter: bool = False) -> Dict:
    """
    Type text into an input field.
    """
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        element = _page_instance.locator(selector)
        
        if clear_first:
            element.clear()
        
        element.type(text)
        
        if press_enter:
            _page_instance.keyboard.press("Enter")
        
        return {
            "success": True,
            "selector": selector,
            "text_length": len(text),
            "pressed_enter": press_enter,
            "message": f"Successfully typed text into {selector}"
        }
        
    except PlaywrightTimeoutError:
        return {
            "success": False,
            "error": f"Input field not found: {selector}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Typing failed: {str(e)}"
        }


def extract_text(selector: str, extract_all: bool = False) -> Dict:
    """
    Extract text content from element(s).
    """
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        if extract_all:
            elements = _page_instance.locator(selector)
            count = elements.count()
            
            if count == 0:
                return {
                    "success": False,
                    "error": f"No elements found matching: {selector}"
                }
            
            texts = []
            for i in range(count):
                text = elements.nth(i).text_content()
                if text and text.strip():
                    texts.append(text.strip())
            
            return {
                "success": True,
                "selector": selector,
                "count": len(texts),
                "texts": texts,
                "message": f"Extracted text from {len(texts)} elements"
            }
        else:
            text = _page_instance.locator(selector).first.text_content()
            
            if not text:
                return {
                    "success": False,
                    "error": f"Element found but contains no text: {selector}"
                }
            
            return {
                "success": True,
                "selector": selector,
                "text": text.strip(),
                "length": len(text.strip()),
                "message": f"Successfully extracted text from {selector}"
            }
        
    except PlaywrightTimeoutError:
        return {
            "success": False,
            "error": f"Element not found: {selector}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Text extraction failed: {str(e)}"
        }


def take_screenshot(filename: str, full_page: bool = False, selector: str = None) -> Dict:
    """
    Take a screenshot of the page or specific element.
    """
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        # Ensure filename has .png extension
        if not filename.endswith('.png'):
            filename = f"{filename}.png"
        
        screenshot_path = SCREENSHOTS_DIR / filename
        
        if selector:
            # Screenshot specific element
            element = _page_instance.locator(selector)
            element.screenshot(path=str(screenshot_path))
            screenshot_type = "element"
        else:
            # Screenshot whole page or viewport
            _page_instance.screenshot(path=str(screenshot_path), full_page=full_page)
            screenshot_type = "full_page" if full_page else "viewport"
        
        return {
            "success": True,
            "path": str(screenshot_path),
            "filename": filename,
            "type": screenshot_type,
            "message": f"Screenshot saved to {screenshot_path}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Screenshot failed: {str(e)}"
        }


def wait_for_element(selector: str, state: str = "visible", timeout: int = 30000) -> Dict:
    """
    Wait for an element to reach a specific state.
    """
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        _page_instance.wait_for_selector(selector, state=state, timeout=timeout)
        
        return {
            "success": True,
            "selector": selector,
            "state": state,
            "message": f"Element {selector} is now {state}"
        }
        
    except PlaywrightTimeoutError:
        return {
            "success": False,
            "error": f"Element did not reach state '{state}' within {timeout}ms: {selector}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Wait failed: {str(e)}"
        }


def get_page_info() -> Dict:
    """
    Get information about the current page.
    """
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        title = _page_instance.title()
        url = _page_instance.url
        viewport = _page_instance.viewport_size
        
        return {
            "success": True,
            "title": title,
            "url": url,
            "viewport": viewport,
            "message": "Page information retrieved successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get page info: {str(e)}"
        }


def close_browser(force: bool = True) -> Dict:
    """
    Close the browser and cleanup resources.
    """
    global _playwright_instance, _browser_instance, _context_instance, _page_instance
    
    try:
        closed_resources = []
        
        if _page_instance:
            _page_instance.close()
            _page_instance = None
            closed_resources.append("page")
        
        if _context_instance:
            _context_instance.close()
            _context_instance = None
            closed_resources.append("context")
        
        if _browser_instance:
            _browser_instance.close()
            _browser_instance = None
            closed_resources.append("browser")
        
        if _playwright_instance:
            _playwright_instance.stop()
            _playwright_instance = None
            closed_resources.append("playwright")
        
        return {
            "success": True,
            "closed": closed_resources,
            "message": f"Browser closed successfully. Cleaned up: {', '.join(closed_resources)}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error closing browser: {str(e)}"
        }


def execute_javascript(script: str, args: List = None) -> Dict:
    """
    Execute custom JavaScript in the page context.
    """
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        if args:
            result = _page_instance.evaluate(script, args)
        else:
            result = _page_instance.evaluate(script)
        
        return {
            "success": True,
            "result": result,
            "script_length": len(script),
            "message": "JavaScript executed successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"JavaScript execution failed: {str(e)}"
        }


def check_browser_status() -> Dict:
    """
    Check if browser is running and healthy.
    Not exposed as a tool - internal use only.
    """
    global _browser_instance, _page_instance
    
    if not _browser_instance or not _page_instance:
        return {
            "running": False,
            "browser_exists": _browser_instance is not None,
            "page_exists": _page_instance is not None
        }
    
    try:
        _page_instance.title()
        return {
            "running": True,
            "url": _page_instance.url,
            "title": _page_instance.title()
        }
    except:
        return {
            "running": False,
            "error": "Browser connection lost"
        }
