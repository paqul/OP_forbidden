import os
import json
import asyncio
import time
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
_current_browser_type = None  # Track which browser is running

# Timeout tracking for orchestrator
_timeout_count = 0  # Track consecutive timeouts


tools = [
    {
        "type": "function",
        "function": {
            "name": "launch_browser",
            "description": "Launch a browser instance with Playwright. Supports Chrome (chromium), Firefox, and WebKit (Safari). Can run in headless or headed mode. Use to start browser or switch to different browser type when timeouts occur. Automatically closes existing browser before launching new one. Returns JSON with browser launch status.",
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
            "description": "Navigate browser to a specific URL. Waits for page to load. Use after launch_browser. On timeout, returns error_type='TIMEOUT' with vpn_switch_recommended=True flag and recommendation message for orchestrator to request VPN switch from VPN LLM. Returns JSON with navigation status and detailed error information.",
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
            "description": "Click on an element on the page. Can use CSS selectors, text content, or accessibility labels. On timeout, returns error_type='TIMEOUT' with vpn_switch_recommended=True and browser_switch_recommended flag (if timeout_count >= 2). Orchestrator should request VPN switch or browser change. Returns JSON with click status and detailed error information.",
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
            "description": "Wait for an element to appear on the page before proceeding. Useful before clicking or extracting. On timeout, returns error_type='TIMEOUT' with vpn_switch_recommended=True and browser_switch_recommended flag (if timeout_count >= 2). Orchestrator should request VPN switch or browser change. Returns JSON with wait status and detailed error information.",
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
            "description": "Get current page information including title, URL, viewport size, current browser type, and list of alternative browsers available for switching. Use this to help orchestrator decide which browser to try next on repeated timeouts. Returns JSON with page and browser details.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "reset_timeout_counter",
            "description": "Reset the consecutive timeout counter to 0. Use after orchestrator requests VPN switch to start fresh tracking. Returns JSON with previous and current count.",
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
            "name": "wait_for_duration",
            "description": "Keep browser alive and wait for specified duration. Use this to monitor video playback, keep page open, or verify long-running processes. Prints progress updates every 30 seconds. IMPORTANT: Use this after starting video to keep it playing. Returns JSON with wait status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "integer",
                        "description": "Number of seconds to wait (e.g., 5000 for ~66 minutes)"
                    },
                    "verify_playing": {
                        "type": "boolean",
                        "description": "Periodically verify video is still playing using JavaScript check (default: True for video monitoring)"
                    },
                    "check_interval": {
                        "type": "integer",
                        "description": "Seconds between status checks (default: 30)"
                    }
                },
                "required": ["seconds"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handle_consent_dialog",
            "description": "Automatically detect and accept cookie consent/GDPR dialogs (like YouTube's 'Accept all' or 'Reject all' buttons). IMPORTANT: Call this RIGHT AFTER navigating to a page and BEFORE clicking play button. Handles common consent patterns on YouTube, social media, and other sites. Returns JSON with acceptance status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Which action to take on consent dialog",
                        "enum": ["accept", "reject", "auto"],
                        "default": "accept"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum time to wait for dialog in milliseconds (default: 5000)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_for_bot_detection",
            "description": "Check if page shows bot detection, captcha, or 'Sign in to confirm you're not a bot' message. CRITICAL: Call this after handle_consent_dialog and BEFORE attempting to interact with page. If detected, returns error with vpn_swap_required=True for orchestrator to request VPN server change. Returns JSON with detection status.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
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


def launch_browser(browser_type: str = "chromium", headless: bool = False, 
                   viewport_width: int = 1920, viewport_height: int = 1080) -> Dict:
    """
    Launch a browser instance with Playwright.
    Supports chromium (Chrome), firefox, and webkit (Safari).
    """
    global _playwright_instance, _browser_instance, _context_instance, _page_instance, _current_browser_type
    
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
        _current_browser_type = browser_type
        
        # User agent to appear as real browser (helps avoid bot detection)
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # Create browser context with viewport and NO STATE (fresh start - no cookies, no cache)
        _context_instance = _browser_instance.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            user_agent=user_agent,
            storage_state=None,  # No stored auth/cookies
            ignore_https_errors=True,  # Ignore SSL errors
            java_script_enabled=True,
            accept_downloads=True,
            locale="en-US",  # Set locale
            timezone_id="Europe/Warsaw"  # Set timezone
        )
        
        # Clear all cookies and storage (double ensure clean state)
        _context_instance.clear_cookies()
        
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
    Returns timeout information that orchestrator can use to decide on VPN switch.
    """
    global _timeout_count
    
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        response = _page_instance.goto(url, wait_until=wait_until, timeout=timeout)
        
        # Get page information
        title = _page_instance.title()
        current_url = _page_instance.url
        
        # Reset timeout count on success
        _timeout_count = 0
        
        return {
            "success": True,
            "url": current_url,
            "title": title,
            "status": response.status if response else None,
            "message": f"Successfully navigated to {url}"
        }
        
    except PlaywrightTimeoutError:
        _timeout_count += 1
        return {
            "success": False,
            "error": f"Navigation timeout after {timeout}ms. Page took too long to load.",
            "error_type": "TIMEOUT",
            "timeout_count": _timeout_count,
            "vpn_switch_recommended": True,
            "recommendation": "Request VPN LLM to switch server and retry navigation",
            "url_attempted": url,
            "timeout_ms": timeout
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Navigation failed: {str(e)}",
            "error_type": "GENERAL",
            "vpn_switch_recommended": False
        }


def click_element(selector: str, timeout: int = 30000, force: bool = False) -> Dict:
    """
    Click on an element using CSS selector, text, or role.
    Reports timeout to orchestrator for VPN/browser switching decisions.
    """
    global _timeout_count
    
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        _page_instance.click(selector, timeout=timeout, force=force)
        
        # Reset timeout count on success
        _timeout_count = 0
        
        return {
            "success": True,
            "selector": selector,
            "message": f"Successfully clicked element: {selector}"
        }
        
    except PlaywrightTimeoutError:
        _timeout_count += 1
        return {
            "success": False,
            "error": f"Element not found or not clickable: {selector} (timeout: {timeout}ms)",
            "error_type": "TIMEOUT",
            "timeout_count": _timeout_count,
            "vpn_switch_recommended": True,
            "browser_switch_recommended": _timeout_count >= 2,
            "recommendation": "Element click timeout. Options: 1) Request VPN LLM to switch server, 2) Try different browser (firefox/chromium) if timeout_count >= 2, 3) Retry operation",
            "selector_attempted": selector,
            "timeout_ms": timeout
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Click failed: {str(e)}",
            "error_type": "GENERAL",
            "vpn_switch_recommended": False
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
    Reports timeout to orchestrator for VPN/browser switching decisions.
    """
    global _timeout_count
    
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        _page_instance.wait_for_selector(selector, state=state, timeout=timeout)
        
        # Reset timeout count on success
        _timeout_count = 0
        
        return {
            "success": True,
            "selector": selector,
            "state": state,
            "message": f"Element {selector} is now {state}"
        }
        
    except PlaywrightTimeoutError:
        _timeout_count += 1
        return {
            "success": False,
            "error": f"Element did not reach state '{state}' within {timeout}ms: {selector}",
            "error_type": "TIMEOUT",
            "timeout_count": _timeout_count,
            "vpn_switch_recommended": True,
            "browser_switch_recommended": _timeout_count >= 2,
            "recommendation": "Wait timeout. Options: 1) Request VPN LLM to switch server, 2) Try different browser (firefox/chromium) if timeout_count >= 2, 3) Retry operation",
            "selector_attempted": selector,
            "state_attempted": state,
            "timeout_ms": timeout
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Wait failed: {str(e)}",
            "error_type": "GENERAL",
            "vpn_switch_recommended": False
        }


def get_page_info() -> Dict:
    """
    Get information about the current page and browser.
    """
    global _current_browser_type
    
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
            "browser_type": _current_browser_type,
            "alternative_browsers": _get_alternative_browsers(_current_browser_type),
            "message": "Page information retrieved successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get page info: {str(e)}"
        }


def _get_alternative_browsers(current_browser: str) -> List[str]:
    """Get list of alternative browsers to try if current one has issues."""
    all_browsers = ["chromium", "firefox", "webkit"]
    if current_browser:
        return [b for b in all_browsers if b != current_browser]
    return all_browsers


def close_browser(force: bool = True) -> Dict:
    """
    Close the browser and cleanup resources.
    """
    global _playwright_instance, _browser_instance, _context_instance, _page_instance, _current_browser_type
    
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
        
        _current_browser_type = None
        
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


def reset_timeout_counter() -> Dict:
    """
    Reset the timeout counter. 
    Useful for orchestrator after VPN switch to start fresh.
    """
    global _timeout_count
    old_count = _timeout_count
    _timeout_count = 0
    
    return {
        "success": True,
        "previous_count": old_count,
        "current_count": 0,
        "message": "Timeout counter reset successfully"
    }


def wait_for_duration(seconds: int, verify_playing: bool = True, check_interval: int = 30) -> Dict:
    """
    Keep browser alive and wait for specified duration.
    Useful for monitoring video playback or keeping page open.
    """
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        start_time = time.time()
        elapsed = 0
        checks_performed = 0
        
        print(f"\n⏱️  Starting wait for {seconds} seconds ({seconds/60:.1f} minutes)...")
        print(f"   Browser will stay open and page will remain active")
        if verify_playing:
            print(f"   Checking video playback status every {check_interval} seconds\n")
        
        while elapsed < seconds:
            # Calculate remaining time
            remaining = seconds - elapsed
            
            # Wait for check_interval or remaining time (whichever is smaller)
            sleep_time = min(check_interval, remaining)
            time.sleep(sleep_time)
            
            elapsed = time.time() - start_time
            checks_performed += 1
            
            # Progress update
            progress_pct = (elapsed / seconds) * 100
            print(f"⏳ [{progress_pct:5.1f}%] Elapsed: {int(elapsed)}s / {seconds}s  |  Remaining: {int(seconds - elapsed)}s")
            
            # Verify video is still playing (if requested)
            if verify_playing and elapsed < seconds:
                try:
                    # Check if video element exists and is playing
                    is_playing = _page_instance.evaluate("""
                        () => {
                            const video = document.querySelector('video');
                            if (video) {
                                return !video.paused && !video.ended && video.readyState > 2;
                            }
                            return false;
                        }
                    """)
                    
                    if is_playing:
                        print(f"   ✅ Video is playing")
                    else:
                        print(f"   ⚠️  Warning: Video may not be playing")
                        return {
                            "success": False,
                            "error": "Video playback verification failed - video paused or ended",
                            "elapsed_seconds": int(elapsed),
                            "total_seconds": seconds,
                            "checks_performed": checks_performed
                        }
                except Exception as e:
                    print(f"   ⚠️  Could not verify video playback: {str(e)}")
        
        total_elapsed = time.time() - start_time
        print(f"\n✅ Wait completed! Total time: {int(total_elapsed)}s ({total_elapsed/60:.1f} minutes)\n")
        
        return {
            "success": True,
            "elapsed_seconds": int(total_elapsed),
            "requested_seconds": seconds,
            "checks_performed": checks_performed,
            "message": f"Successfully waited {int(total_elapsed)} seconds"
        }
        
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⚠️  Wait interrupted by user after {int(elapsed)} seconds\n")
        return {
            "success": False,
            "error": "Wait interrupted by user",
            "elapsed_seconds": int(elapsed),
            "requested_seconds": seconds
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Wait failed: {str(e)}"
        }


def handle_consent_dialog(action: str = "accept", timeout: int = 5000) -> Dict:
    """
    Automatically detect and handle cookie consent/GDPR dialogs.
    Tries multiple common selectors for YouTube and other sites.
    """
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        # Common consent dialog button selectors (ordered by priority)
        # YouTube specific patterns
        consent_selectors = {
            "accept": [
                "button:has-text('Accept all')",  # YouTube English
                "button:has-text('Akceptuj wszystko')",  # YouTube Polish
                "button:has-text('Accepter tout')",  # YouTube French
                "button:has-text('Aceptar todas')",  # YouTube Spanish
                "button:has-text('Alle akzeptieren')",  # YouTube German
                "[aria-label*='Accept']",
                "button[aria-label*='Accept all']",
                "button[aria-label*='Consent']",
                "//button[contains(., 'Accept all')]",
                "//button[contains(., 'Accept')]",
                ".consent-accept",
                "#accept-button",
                "[data-action='accept']",
            ],
            "reject": [
                "button:has-text('Reject all')",  # YouTube English
                "button:has-text('Odrzuć wszystko')",  # YouTube Polish
                "button:has-text('Tout rejeter')",  # YouTube French
                "button:has-text('Rechazar todas')",  # YouTube Spanish
                "button:has-text('Alle ablehnen')",  # YouTube German
                "[aria-label*='Reject']",
                "button[aria-label*='Reject all']",
                "//button[contains(., 'Reject all')]",
                "//button[contains(., 'Reject')]",
                ".consent-reject",
                "#reject-button",
            ]
        }
        
        # Auto mode: try accept first, if not found try reject
        if action == "auto":
            selectors_to_try = consent_selectors["accept"] + consent_selectors["reject"]
        else:
            selectors_to_try = consent_selectors.get(action, consent_selectors["accept"])
        
        print(f"\n🔍 Looking for consent dialog ({action} action)...")
        
        # Try each selector
        for selector in selectors_to_try:
            try:
                # Check if element exists and is visible
                element = _page_instance.locator(selector).first
                
                # Wait briefly for element to be visible
                if element.is_visible(timeout=timeout):
                    print(f"   ✅ Found consent button: {selector}")
                    
                    # Click the button
                    element.click(timeout=3000)
                    
                    # Wait a moment for dialog to disappear
                    time.sleep(1)
                    
                    print(f"   ✅ Clicked consent button successfully")
                    
                    return {
                        "success": True,
                        "action": action,
                        "selector_used": selector,
                        "message": f"Successfully handled consent dialog with action: {action}"
                    }
            except Exception:
                # This selector didn't work, try next one
                continue
        
        # No consent dialog found - might not be present
        print(f"   ℹ️  No consent dialog found (this is OK if none exists)")
        return {
            "success": True,
            "action": action,
            "selector_used": None,
            "found": False,
            "message": "No consent dialog found - page may not require consent or dialog already handled"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Consent dialog handling failed: {str(e)}",
            "action": action
        }


def check_for_bot_detection() -> Dict:
    """
    Check if page displays bot detection, captcha, or sign-in requirements.
    Returns error with vpn_swap_required if bot detection is found.
    """
    check_success, check_error = _ensure_browser_running()
    if not check_success:
        return {"success": False, "error": check_error}
    
    try:
        print(f"\n🤖 Checking for bot detection or captcha...")
        
        # Bot detection patterns (YouTube and generic)
        bot_detection_patterns = [
            # YouTube specific
            "Sign in to confirm you're not a bot",
            "Sign in to confirm you're not a bot",
            "Zaloguj się, aby potwierdzić, że nie jesteś botem",  # Polish
            "Connectez-vous pour confirmer que vous n'êtes pas un robot",  # French
            "Inicia sesión para confirmar que no eres un bot",  # Spanish
            "Melden Sie sich an, um zu bestätigen, dass Sie kein Bot sind",  # German
            
            # Generic patterns
            "confirm you're not a bot",
            "verify you're not a robot",
            "prove you're human",
            "captcha",
            "I'm not a robot",
            "unusual traffic",
            "suspicious activity",
            "automated requests",
        ]
        
        # Get page text content
        page_text = _page_instance.evaluate("() => document.body.innerText")
        page_text_lower = page_text.lower()
        
        # Check for bot detection patterns
        detected_pattern = None
        for pattern in bot_detection_patterns:
            if pattern.lower() in page_text_lower:
                detected_pattern = pattern
                break
        
        if detected_pattern:
            print(f"   🚨 BOT DETECTION FOUND: '{detected_pattern}'")
            print(f"   ⚠️  Current VPN IP is flagged/blocked")
            
            return {
                "success": False,
                "error": "Bot detection encountered",
                "error_type": "BOT_DETECTION",
                "detected_pattern": detected_pattern,
                "vpn_swap_required": True,
                "recommendation": "STOP current task. Request orchestrator to ask VPN LLM to connect to different server, then retry navigation.",
                "message": f"Page shows bot detection: '{detected_pattern}'. VPN IP is likely flagged."
            }
        
        # Also check for common captcha elements
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='captcha']",
            ".g-recaptcha",
            "#recaptcha",
            "[data-sitekey]",  # reCAPTCHA
            ".captcha-container",
        ]
        
        for selector in captcha_selectors:
            try:
                if _page_instance.locator(selector).first.is_visible(timeout=1000):
                    print(f"   🚨 CAPTCHA DETECTED: {selector}")
                    
                    return {
                        "success": False,
                        "error": "CAPTCHA encountered",
                        "error_type": "CAPTCHA",
                        "captcha_selector": selector,
                        "vpn_swap_required": True,
                        "recommendation": "STOP current task. Request orchestrator to ask VPN LLM to connect to different server, then retry navigation.",
                        "message": f"Page shows CAPTCHA challenge. VPN IP is likely flagged."
                    }
            except Exception:
                continue
        
        # No bot detection found
        print(f"   ✅ No bot detection or captcha found")
        return {
            "success": True,
            "bot_detected": False,
            "message": "Page is accessible, no bot detection found"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Bot detection check failed: {str(e)}"
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
