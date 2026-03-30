#!/usr/bin/env python3
"""
Debug script to help identify IDE vs terminal environment differences.
Run this in both IDE and terminal to compare outputs.
"""

import os
import sys
from pathlib import Path

print("=== Environment Debug Script ===")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Current working directory: {Path.cwd()}")
print(f"Script location: {Path(__file__).parent}")

print("\n=== Environment Variables ===")
env_vars = [
    "BUILD_STREAM_CLIENT_ID",
    "BUILD_STREAM_CLIENT_SECRET",
    "BUILD_STREAM_AUTH_PASSWORD",
    "BUILD_STREAM_BASE_URL",
    "BUILD_STREAM_AUTH_USERNAME",
    "BUILD_STREAM_CLIENT_SCOPES"
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if "SECRET" in var or "PASSWORD" in var:
            display_value = value[:4] + "*" * (len(value) - 4)
        else:
            display_value = value
        print(f"✅ {var}: {display_value}")
    else:
        print(f"❌ {var}: Not set")

print("\n=== .env File Search ===")
env_paths = [
    Path(__file__).parent.parent.parent / ".env",
    Path.cwd() / ".env",
    Path.cwd().parent / ".env",
    Path("/opt/omnia/windsurf/build_stream_venu_oim/build_stream/.env"),
]

for i, env_file in enumerate(env_paths, 1):
    exists = env_file.exists()
    print(f"{i}. {env_file} - {'✅ EXISTS' if exists else '❌ NOT FOUND'}")

print("\n=== python-dotenv Test ===")
try:
    from dotenv import load_dotenv
    print("✅ python-dotenv is available")

    # Test loading from the first available .env
    for env_file in env_paths:
        if env_file.exists():
            print(f"Testing load from: {env_file}")
            load_dotenv(env_file)

            # Check if variables are now loaded
            client_id = os.getenv("BUILD_STREAM_CLIENT_ID")
            if client_id:
                print("✅ Successfully loaded environment variables")
            else:
                print("❌ Failed to load environment variables")
            break
except ImportError:
    print("❌ python-dotenv not available")

print("\n=== PYTHONPATH ===")
for path in sys.path[:5]:  # Show first 5 paths
    print(f"  {path}")

print("\n=== IDE vs Terminal Diagnosis ===")
print("If you see differences between IDE and terminal:")
print("1. Check if IDE uses different Python interpreter")
print("2. Check if IDE has different working directory")
print("3. Check if IDE has different PYTHONPATH")
print("4. Check if IDE has different environment variables")
