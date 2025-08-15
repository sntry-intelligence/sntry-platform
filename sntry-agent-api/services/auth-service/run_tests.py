#!/usr/bin/env python3
"""
Test runner for authentication service
"""
import sys
import os
import subprocess

# Add the parent directory to the path so we can import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

def run_tests():
    """Run all tests for the authentication service"""
    print("Running authentication service tests...")
    
    # Change to the auth service directory
    os.chdir(os.path.dirname(__file__))
    
    # Run pytest with verbose output
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/", 
        "-v", 
        "--tb=short",
        "--disable-warnings"
    ], capture_output=False)
    
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)