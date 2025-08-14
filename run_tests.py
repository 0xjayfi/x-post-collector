#!/usr/bin/env python3
"""Test runner for discord-to-sheets project.

Usage:
    python run_tests.py         # Run all tests
    python run_tests.py unit     # Run only unit tests
    python run_tests.py integration  # Run only integration tests
"""

import sys
import subprocess
import os


def run_unit_tests():
    """Run unit tests."""
    print("=" * 60)
    print("Running Unit Tests")
    print("=" * 60)
    
    venv_python = "./venv/bin/python"
    
    result = subprocess.run(
        [venv_python, "-m", "unittest", "tests.test_discord_handler", "-v"],
        capture_output=False
    )
    
    return result.returncode == 0


def run_integration_tests():
    """Run integration tests."""
    print("\n" + "=" * 60)
    print("Running Integration Tests")
    print("=" * 60)
    
    venv_python = "./venv/bin/python"
    
    result = subprocess.run(
        [venv_python, "test_discord_integration.py"],
        capture_output=False
    )
    
    return result.returncode == 0


def main():
    """Main test runner."""
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "unit":
            success = run_unit_tests()
        elif test_type == "integration":
            success = run_integration_tests()
        else:
            print(f"Unknown test type: {test_type}")
            print("Usage: python run_tests.py [unit|integration]")
            sys.exit(1)
    else:
        # Run all tests
        unit_success = run_unit_tests()
        integration_success = run_integration_tests()
        success = unit_success and integration_success
        
    if success:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()