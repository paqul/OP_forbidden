"""
Test script to demonstrate the logging system.
Run this to see how logging captures LLM execution details.
"""

if __name__ == "__main__":
    print("Starting LLM Execution with Logging...")
    print("Check the 'logs' folder for detailed log files.\n")
    
    import llm_vpn_execution
    
    # Run the LLM execution - all actions will be logged
    llm_vpn_execution.run()
    
    print("\n✅ Execution complete! Check the logs folder for detailed execution logs.")
