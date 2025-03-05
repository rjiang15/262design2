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
        
        # Create the log directory
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
    
    @unittest.skip("This test spawns actual processes and is time-consuming")
    def test_run_vm_process(self):
        """Test running a VM in a separate process."""
        # Find the path to run_vm.py
        run_vm_path = os.path.join(os.path.dirname(__file__), "..", "run_vm.py")
        
        # Run a VM process for a short duration
        process = subprocess.Popen([
            sys.executable,
            run_vm_path,
            "--vm_id", "1",
            "--tick_rate", "10",
            "--base_port", "5000",
            "--duration", "2",  # Run for 2 seconds
            "--send_threshold", "3",
            "--total_vms", "1"
        ])
        
        # Wait for the process to complete
        process.wait()
        
        # Verify log file was created
        log_files = glob.glob(os.path.join(self.log_dir, "*.log"))
        self.assertEqual(len(log_files), 1)
        
        # Verify log file contains events
        with open(log_files[0], "r") as f:
            log_content = f.read()
        self.assertIn("Internal event", log_content)
    
    @unittest.skip("This test spawns multiple processes and is time-consuming")
    def test_multiple_vms(self):
        """Test running multiple VMs that communicate with each other."""
        # Find the path to main.py
        main_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
        
        # Run the simulation for a short duration
        process = subprocess.Popen([
            sys.executable,
            main_path,
            "--num_vms", "3",
            "--duration", "5",  # Run for 5 seconds
            "--tick_rates", "5,10,15",
            "--send_threshold", "3"
        ])
        
        # Wait for the process to complete
        process.wait()
        
        # Verify log files were created
        log_files = glob.glob(os.path.join(self.log_dir, "*.log"))
        self.assertEqual(len(log_files), 0)  # Logs should be cleared and archived
        
        # Verify archive file was created
        archive_files = glob.glob(os.path.join(self.archive_dir, "*.csv"))
        self.assertEqual(len(archive_files), 1)
        
        # Verify CSV contains events from all VMs
        with open(archive_files[0], "r", newline="") as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
        
        # Extract VM IDs
        vm_ids = set(row[2] for row in rows[1:])
        self.assertEqual(vm_ids, {"1", "2", "3"})

if __name__ == "__main__":
    unittest.main()