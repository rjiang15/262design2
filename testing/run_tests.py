#!/usr/bin/env python3
import unittest
import os
import sys

# ANSI escape codes for colored output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

class ColorTextTestResult(unittest.TextTestResult):
    def addSuccess(self, test):
        super().addSuccess(test)
        self.stream.writeln(f"{GREEN}SUCCESS: {test}{RESET}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.stream.writeln(f"{RED}FAILURE: {test}{RESET}")

    def addError(self, test, err):
        super().addError(test, err)
        self.stream.writeln(f"{RED}ERROR: {test}{RESET}")

class ColorTextTestRunner(unittest.TextTestRunner):
    resultclass = ColorTextTestResult

if __name__ == "__main__":
    # Discover all test files in the current testing directory
    test_loader = unittest.TestLoader()
    # Assumes run_tests.py is located in the testing directory
    test_suite = test_loader.discover(start_dir=os.path.dirname(__file__), pattern="test_*.py")
    
    # Run tests with the custom colored test runner
    runner = ColorTextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return an appropriate exit code based on the test results
    sys.exit(not result.wasSuccessful())
