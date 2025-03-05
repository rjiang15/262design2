#!/usr/bin/env python3
import unittest
import os
import sys

def run_tests():
    """
    Discover and run all tests in the tests directory.
    """
    # Determine the test directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add the project root directory to the path so imports work
    project_root = os.path.abspath(os.path.join(test_dir, ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Create test suite from all test files
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern="test_*.py")
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return 0 if all tests passed, 1 otherwise
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests())