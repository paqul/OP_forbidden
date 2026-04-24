# Multi-Agent AI Orchestrator

Advanced multi-agent system with specialized LLM agents for VPN management and browser automation.

## Features

### 🤖 Multi-Agent Architecture
- **Main Orchestrator:** Routes tasks to specialized agents based on user requests
- **VPN Agent:** Manages Mullvad VPN connections with WireGuard
- **Browser Agent:** Controls browsers with Playwright for web automation

### 🌐 VPN Management
- Connect/disconnect from Mullvad VPN servers worldwide
- List available servers with real-time status
- Persistent connections between orchestrator tasks
- WireGuard key reuse to avoid API limits
- Automatic public IP and location detection

### 🌍 Browser Automation
- Launch and control Chromium/Firefox/WebKit browsers
- Navigate to websites and interact with elements
- Extract data and scrape web pages
- Take screenshots for monitoring
- Execute custom JavaScript
- Persistent browser sessions between tasks

### 📝 Comprehensive Logging
- All LLM requests/responses logged
- Tool execution tracking
- Timestamped log files
- Session summaries with statistics

## Quick Start

### 1. Install Dependencies
```powershell
# Python packages
pip install openai playwright requests

# Playwright browser binaries
python -m playwright install chromium
```

### 2. Configure API Keys
Edit `keys/projects_api_keys.py`:
```python
open_ai_api_key = "your-openai-api-key"
mullvad_account = "your-mullvad-account-number"
```

### 3. Run Main Orchestrator
```powershell
python main.py
```

The orchestrator will automatically route tasks to the appropriate agent.

## Project Structure

```
OP_forbidden/
├── main.py                          # Main orchestrator (routes to agents)
├── llm_vpn_execution.py             # VPN agent LLM execution loop
├── llm_playwright_execution.py      # Browser agent LLM execution loop
├── vpn_tools.py                     # VPN functions (Mullvad + WireGuard)
├── playwright_tools.py              # Browser automation functions
├── test_browser_integration.py      # Browser integration tests
├── prompts/
│   └── system_prompts.py            # System prompts for all agents
├── keys/
│   └── projects_api_keys.py         # API keys configuration
├── logger/
│   └── logger_file.py               # Logging system
├── logs/                            # Execution logs
├── screenshots/                     # Browser screenshots
├── scraped_data/                    # Extracted web data
├── tests/                           # VPN tests
└── vpns/                            # VPN documentation
```

## Documentation

- **[BROWSER_INTEGRATION_COMPLETE.md](BROWSER_INTEGRATION_COMPLETE.md)** - Complete browser integration guide
- **[PLAYWRIGHT_SETUP.md](PLAYWRIGHT_SETUP.md)** - Playwright setup and usage
- **[vpns/QUICK_START.md](vpns/QUICK_START.md)** - VPN quick start guide
- **[vpns/VPN_API_DOCUMENTATION.md](vpns/VPN_API_DOCUMENTATION.md)** - VPN API reference
- **[logger/LOGGING_GUIDE.md](logger/LOGGING_GUIDE.md)** - Logging system guide

## Usage Examples

### VPN Tasks
```python
# Connect to VPN in Germany
"Connect to a VPN server in Germany"

# Check VPN status
"Check my current VPN connection status"

# Disconnect VPN
"Disconnect from VPN"
```

### Browser Tasks
```python
# Take screenshot
"Navigate to example.com and take a screenshot"

# Extract data
"Go to news.ycombinator.com and extract all article titles"

# Fill form
"Navigate to Google, search for 'Python tutorials', and screenshot the results"
```

### Combined Tasks
```python
# VPN + Browser
"Connect to VPN in Japan, then visit whatismyip.com and screenshot the page"
```

## Architecture

The system uses a hierarchical multi-agent architecture:

1. **User Request** → Main Orchestrator (GPT-4o-mini)
2. **Orchestrator Analyzes** → Routes to appropriate agent
3. **Specialized Agent** → Executes task with tool calls
4. **Agent Returns** → Result back to orchestrator
5. **Orchestrator** → Provides final response to user

### Agent Behavior
- **Task-Oriented:** Agents execute only what the orchestrator requests
- **Persistent Resources:** VPN connections and browser sessions stay open between tasks
- **Smart Management:** Agents check resource status before creating new ones
- **No Autonomy:** Agents don't take extra actions beyond the task

## Requirements

- Python 3.10+
- OpenAI API access (GPT-4o-mini)
- Mullvad VPN account (for VPN features)
- WireGuard installed (C:\Program Files\WireGuard\)
- Administrator privileges (for VPN operations)

## Testing

### Test Browser Integration
```powershell
python test_browser_integration.py
```

### Test VPN Functions
```powershell
python tests/safe_vpn_test.py
```

## License

Private project

## Status

✅ Multi-agent orchestration working
✅ VPN agent with Mullvad API integration
✅ Browser agent with Playwright automation
✅ Comprehensive logging system
✅ Persistent resource management
✅ Task-oriented agent behavior

**Ready for production use! 🚀**