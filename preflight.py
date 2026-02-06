#!/usr/bin/env python3
"""
Pre-Flight Checklist - Validate Setup Before Running
"""

import os
import sys
import json

def check_python_version():
    """Check Python version is 3.7+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Python 3.7+ required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """Check required packages are installed"""
    required = ['pandas', 'numpy', 'requests']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✓ {package} installed")
        except ImportError:
            missing.append(package)
            print(f"❌ {package} NOT installed")
    
    if missing:
        print()
        print("Install missing packages:")
        print(f"  pip install {' '.join(missing)} --break-system-packages")
        return False
    
    return True

def check_api_credentials():
    """Check API credentials are set"""
    key_name = os.getenv('COINBASE_API_KEY_NAME')
    private_key = os.getenv('COINBASE_PRIVATE_KEY')
    
    if not key_name:
        print("❌ COINBASE_API_KEY_NAME not set")
        print("   Set with: export COINBASE_API_KEY_NAME='your_key_name'")
        return False
    
    if not private_key:
        print("❌ COINBASE_PRIVATE_KEY not set")
        print("   Set with: export COINBASE_PRIVATE_KEY='your_private_key'")
        return False
    
    if not private_key.startswith('-----BEGIN'):
        print("⚠️  WARNING: Private key should be in PEM format")
        print("   It should start with: -----BEGIN EC PRIVATE KEY-----")
    
    print("✓ API credentials found")
    print(f"   Key Name: {key_name}")
    return True

def check_config():
    """Validate config.json"""
    if not os.path.exists('config.json'):
        print("⚠️  config.json not found (will use defaults)")
        return True
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        print("✓ config.json valid")
        
        # Check paper trading mode
        if config.get('paper_trading', {}).get('enabled', True):
            print("✓ Paper trading ENABLED (safe mode)")
        else:
            print("⚠️  LIVE TRADING ENABLED - REAL MONEY AT RISK!")
            response = input("   Are you sure? (type 'YES' to continue): ")
            if response != 'YES':
                print("   Aborted by user")
                return False
        
        return True
    except json.JSONDecodeError:
        print("❌ config.json is invalid JSON")
        return False

def check_file_permissions():
    """Check script has execute permissions"""
    if os.access('crypto_agent.py', os.R_OK):
        print("✓ crypto_agent.py readable")
    else:
        print("❌ crypto_agent.py not readable")
        return False
    
    return True

def main():
    """Run all checks"""
    print("=" * 60)
    print("PRE-FLIGHT CHECKLIST")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("API Credentials", check_api_credentials),
        ("Configuration", check_config),
        ("File Permissions", check_file_permissions),
    ]
    
    all_passed = True
    
    for name, check_func in checks:
        print(f"[{name}]")
        if not check_func():
            all_passed = False
        print()
    
    print("=" * 60)
    
    if all_passed:
        print("✅ ALL CHECKS PASSED")
        print()
        print("Ready to run:")
        print("  python3 crypto_agent.py")
        print()
        print("Or use the quick-start script:")
        print("  ./run.sh")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print()
        print("Fix the issues above before running the agent.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
