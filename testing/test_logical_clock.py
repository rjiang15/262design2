#!/usr/bin/env python3
import unittest
import sys
import os

# Add the src directory to the path so we can import the modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from logical_clock import LogicalClock

class TestLogicalClock(unittest.TestCase):
    """Test cases for the LogicalClock class."""
    
    def test_init(self):
        """Test initialization with default and custom values."""
        # Test default initialization
        clock = LogicalClock()
        self.assertEqual(clock.time, 0)
        
        # Test initialization with a custom value
        clock = LogicalClock(initial=5)
        self.assertEqual(clock.time, 5)
    
    def test_tick(self):
        """Test that tick increments the clock by 1."""
        clock = LogicalClock(initial=10)
        new_time = clock.tick()
        self.assertEqual(new_time, 11)
        self.assertEqual(clock.time, 11)
        
        # Test multiple ticks
        clock.tick()
        self.assertEqual(clock.time, 12)
    
    def test_update(self):
        """Test that update sets the clock to max(local, received) + 1."""
        # Case 1: received time < local time
        clock = LogicalClock(initial=10)
        new_time = clock.update(5)
        self.assertEqual(new_time, 11)
        self.assertEqual(clock.time, 11)
        
        # Case 2: received time > local time
        clock = LogicalClock(initial=10)
        new_time = clock.update(15)
        self.assertEqual(new_time, 16)
        self.assertEqual(clock.time, 16)
        
        # Case 3: received time = local time
        clock = LogicalClock(initial=10)
        new_time = clock.update(10)
        self.assertEqual(new_time, 11)
        self.assertEqual(clock.time, 11)
    
    def test_get_time(self):
        """Test that get_time returns the current time without modifying it."""
        clock = LogicalClock(initial=42)
        current_time = clock.get_time()
        self.assertEqual(current_time, 42)
        # Verify the internal time didn't change
        self.assertEqual(clock.time, 42)

# Custom test runner with colored output (green for success, red for failure/error)
if __name__ == "__main__":
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
    
    unittest.main(testRunner=ColorTextTestRunner(verbosity=2))
