"""Test key reuse functionality"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpn_tools import get_stored_keys_info, clear_all_stored_keys
import json

# Check current stored keys
print("="*60)
print("STORED WIREGUARD KEYS INFO")
print("="*60)
info = get_stored_keys_info()
print(json.dumps(info, indent=2))

print("\n" + "="*60)
print("CLEARING ALL STORED KEYS")
print("="*60)
# Uncomment to clear keys:
# result = clear_all_stored_keys()
# print(json.dumps(result, indent=2))
print("Run clear_all_stored_keys() to wipe and start fresh")
