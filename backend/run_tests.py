#!/usr/bin/env python3
"""
Test runner script for the backend application.
This script provides an easy way to run tests with different configurations.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_tests(test_type="all", coverage=True, verbose=True):
    """
    Run tests with specified configuration.
    
    Args:
        test_type (str): Type of tests to run ('all', 'unit', 'integration')
        coverage (bool): Whether to run with coverage reporting
        verbose (bool): Whether to run in verbose mode
    """
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])
    
    # Add verbose flag
    if verbose:
        cmd.append("-v")
    
    # Add test type filters
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "auth":
        cmd.extend(["-m", "auth"])
    elif test_type == "api":
        cmd.extend(["-m", "api"])
    elif test_type == "crud":
        cmd.extend(["-m", "crud"])
    elif test_type == "models":
        cmd.extend(["-m", "models"])
    elif test_type == "security":
        cmd.extend(["-m", "security"])
    
    # Add tests directory
    cmd.append("tests/")
    
    print(f"Running tests: {' '.join(cmd)}")
    
    # Run the tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode

def main():
    """Main function to handle command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run backend tests")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "auth", "api", "crud", "models", "security"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--no-coverage", 
        action="store_true",
        help="Run tests without coverage reporting"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true",
        help="Run tests in quiet mode"
    )
    
    args = parser.parse_args()
    
    # Run tests
    exit_code = run_tests(
        test_type=args.type,
        coverage=not args.no_coverage,
        verbose=not args.quiet
    )
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 