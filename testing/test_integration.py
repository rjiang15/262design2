#!/usr/bin/env python3
import unittest
import sys
import os
import tempfile
import time
import subprocess
import glob
import csv
from unittest.mock import patch

# Add the src directory to the path so we can import the modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import archive_logs
from logical_clock import LogicalClock
from virtual_machine import VirtualMachine

class TestIntegration(unittest.TestCase):
    """Integration tests for the distributed logical clock system."""
    
    def setUp(self):
        """Set up a temporary directory for logs."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = os.path.join(self.temp_dir.name, "logs")
        self.archive_dir = os.path.join(self.temp_dir.name, "archives")
        
        # Create the log and archive directories
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
        
        # Store original directories to restore later
        self.orig_log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        self.orig_archive_dir = os.path.join(os.path.dirname(__file__), "..", "archives")
        
        # Patch os.path.join to redirect log files to our temp directory
        self.original_join = os.path.join
        def patched_join(*args):
            if len(args) >= 2:
                if args[-2:] == ('..', 'logs'):
                    return self.log_dir
                elif args[-2:] == ('..', 'archives'):
                    return self.archive_dir
            return self.original_join(*args)
        os.path.join = patched_join
    
    def tearDown(self):
        """Clean up after tests."""
        # Restore original os.path.join
        os.path.join = self.original_join
        self.temp_dir.cleanup()
    
    def test_logical_clock_integration(self):
        """Test that LogicalClock integrates correctly with VirtualMachine."""
        # Create two VMs
        vm1 = VirtualMachine(vm_id=1, tick_rate=10, send_threshold=1)
        vm2 = VirtualMachine(vm_id=2, tick_rate=10, send_threshold=1)
        
        # Set up peers directly (in-memory)
        vm1.peers = [vm2]
        vm2.peers = [vm1]
        
        # Run a few ticks on each VM
        for _ in range(5):
            vm1.run_tick()
            vm2.run_tick()
        
        # Verify that each VM's clock has advanced
        self.assertGreater(vm1.clock.get_time(), 0)
        self.assertGreater(vm2.clock.get_time(), 0)
        
        # Clean up
        vm1.shutdown()
        vm2.shutdown()
    
    def test_message_passing(self):
        """Test message passing between VMs."""
        # Create two VMs
        vm1 = VirtualMachine(vm_id=1, tick_rate=10, send_threshold=1)
        vm2 = VirtualMachine(vm_id=2, tick_rate=10, send_threshold=1)
        
        # Set up peers directly (in-memory)
        vm1.peers = [vm2]
        vm2.peers = [vm1]
        
        # Set initial clock values
        vm1.clock.time = 5
        vm2.clock.time = 3
        
        # VM1 sends a message to VM2
        vm1.send_message(vm2, {})
        
        # Process the message in VM2
        self.assertEqual(len(vm2.msg_queue), 1)
        vm2.process_message(vm2.msg_queue[0])
        
        # VM2's clock should now be max(3, 5) + 1 = 6
        self.assertEqual(vm2.clock.get_time(), 6)
        
        # Clean up
        vm1.shutdown()
        vm2.shutdown()
    
    def test_logging_and_archiving(self):
        """Test logging events and archiving logs."""
        # Create a VM
        vm = VirtualMachine(vm_id=1, tick_rate=10, send_threshold=1)
        
        # Log some events
        vm.log_event("Test event 1")
        vm.log_event("Test event 2")
        
        # Shutdown VM to close the log file
        vm.shutdown()
        
        # Verify log file was created
        log_files = glob.glob(os.path.join(self.log_dir, "*.log"))
        self.assertEqual(len(log_files), 1)
        
        # Archive logs
        archive_logs.archive_logs(
            log_dir=self.log_dir,
            archive_dir=self.archive_dir,
            archive_filename_prefix="test_archive"
        )
        
        # Verify archive file was created
        archive_files = glob.glob(os.path.join(self.archive_dir, "*.csv"))
        self.assertEqual(len(archive_files), 1)
        
        # Verify CSV contents
        with open(archive_files[0], "r", newline="") as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
        
        # Check header row
        self.assertEqual(rows[0], ["Timestamp", "Event", "VM_ID"])
        
        # Check that all log entries were archived
        self.assertGreater(len(rows), 1)
        
        # Clear logs
        archive_logs.clear_logs(log_dir=self.log_dir)
        
        # Verify logs were cleared
        log_files = glob.glob(os.path.join(self.log_dir, "*.log"))
        self.assertEqual(len(log_files), 0)
    
    def test_deterministic_scenarios(self):
        """Test deterministic behavior by parameterizing scenarios and removing randomness."""
        scenarios = [
            {
                "desc": "Force internal event (no message sending)",
                "send_threshold": 4,  # Allows random.randint(1,4) to produce 4
                "rand_value": 4,      # This forces the else clause (internal_event)
                "initial_clock_vm1": 10,
                "initial_clock_vm2": 20,
                "expected_vm1": 11,   # internal_event calls clock.tick() => +1
                "action": "internal"
            },
            {
                "desc": "Force message event (send to first peer)",
                "send_threshold": 3,  # random.randint(1,3) returns 1
                "rand_value": 1,      # This forces sending a message
                "initial_clock_vm1": 10,
                "initial_clock_vm2": 20,
                "expected_vm1": 11,   # After sending, vm1's clock ticks
                "expected_vm2": max(20, 10) + 1,  # When vm2 processes message: max(20, 10) + 1 = 21
                "action": "send"
            }
        ]
        
        for scenario in scenarios:
            with self.subTest(scenario=scenario["desc"]):
                # Create two VMs with controlled send_threshold
                vm1 = VirtualMachine(vm_id=1, tick_rate=10, send_threshold=scenario["send_threshold"])
                vm2 = VirtualMachine(vm_id=2, tick_rate=10, send_threshold=scenario["send_threshold"])
                # Set initial clock values
                vm1.clock.time = scenario["initial_clock_vm1"]
                vm2.clock.time = scenario["initial_clock_vm2"]
                # Set up peers
                vm1.peers = [vm2]
                vm2.peers = [vm1]
                # Patch random.randint to force a specific event outcome
                with patch('random.randint', return_value=scenario["rand_value"]):
                    vm1.run_tick()
                
                if scenario["action"] == "send":
                    # For a send event, vm1 sends a message so vm2 should have a queued message
                    self.assertEqual(len(vm2.msg_queue), 1)
                    # Process the message in vm2 and verify its clock update
                    vm2.process_message(vm2.msg_queue[0])
                    self.assertEqual(vm2.clock.get_time(), scenario["expected_vm2"])
                else:
                    # For an internal event, simply check that vm1's clock incremented by one.
                    self.assertEqual(vm1.clock.get_time(), scenario["expected_vm1"])
                
                vm1.shutdown()
                vm2.shutdown()
    

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
