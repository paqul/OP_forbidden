"""
Quick test to verify browser launches in visible mode (not headless).
You should see a Chrome browser window appear for 5 seconds.
"""

import playwright_tools
import time

print("Launching browser in visible mode...")
result = playwright_tools.launch_browser(browser_type="webkit")

print(f"\nBrowser launched!")
print(f"  - Type: {result.get('browser_type')}")
print(f"  - Headless: {result.get('headless')}")
print(f"  - Mode: {'HIDDEN (headless)' if result.get('headless') else 'VISIBLE (headed)'}")
print(f"\nBrowser window should be VISIBLE on your screen now!")
print("Keeping browser open for 5 seconds so you can see it...")

time.sleep(5)

print("\nClosing browser...")
playwright_tools.close_browser()
print("Browser closed.")
