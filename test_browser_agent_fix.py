"""
Test to verify browser agent now takes action instead of asking questions.
"""
import llm_playwright_execution

# Simulate the same task that failed before
user_message = "Navigate to YouTube video https://www.youtube.com/watch?v=ULjo6JaFTWg, extract the video title and take a screenshot"

print("="*70)
print("TESTING BROWSER AGENT WITH NEW ACTION-ORIENTED PROMPT")
print("="*70)
print(f"\nTask: {user_message}\n")
print("Expected: Browser agent should immediately launch browser and take action")
print("Previous behavior: Asked for URL even though it was provided\n")
print("="*70)
print("\nExecuting...\n")

result = llm_playwright_execution.run(user_message)

print("\n" + "="*70)
print("RESULT SUMMARY")
print("="*70)
print(f"Success: {result.get('success')}")
print(f"Browser Launched: {result.get('browser_launched')}")
print(f"Current URL: {result.get('current_url')}")
print(f"Tools Executed: {len(result.get('tools_executed', []))}")
print(f"Iterations: {result.get('iterations')}")

if result.get('tools_executed'):
    print("\nTools Used:")
    for tool in result.get('tools_executed', []):
        print(f"  - {tool['name']}: {'✅' if tool.get('success') else '❌'}")

print("="*70)

# Check if it actually did something
if result.get('browser_launched') and len(result.get('tools_executed', [])) > 0:
    print("\n✅ TEST PASSED: Browser agent took action!")
else:
    print("\n❌ TEST FAILED: Browser agent still not taking action")
