#!/usr/bin/env python3
import sys
print("Step 1: Script started")

try:
    import attacklab
    print("Step 2: attacklab imported OK")
    print(f"  - SERVER_NAME: {attacklab.SERVER_NAME}")
    print(f"  - REQUESTD_PORT: {attacklab.REQUESTD_PORT}")
    print(f"  - RESULTD_PORT: {attacklab.RESULTD_PORT}")
except Exception as e:
    print(f"Step 2 FAILED: {e}")
    sys.exit(1)

try:
    import aiohttp
    print("Step 3: aiohttp imported OK")
    print(f"  - aiohttp version: {aiohttp.__version__}")
except Exception as e:
    print(f"Step 3 FAILED: {e}")
    sys.exit(1)

try:
    import asyncio
    print("Step 4: asyncio imported OK")
except Exception as e:
    print(f"Step 4 FAILED: {e}")
    sys.exit(1)

try:
    import os
    print("Step 5: Checking files...")
    files = ['attacklab-requestd.py', 'attacklab-resultd.py']
    for f in files:
        if os.path.exists(f):
            print(f"  ✓ Found {f}")
        else:
            print(f"  ✗ Missing {f}")
except Exception as e:
    print(f"Step 5 FAILED: {e}")

print("\nStep 6: Testing attacklab.log_msg...")
attacklab.QUIET = False
attacklab.log_msg("Test message")

print("\nAll basic tests passed!")