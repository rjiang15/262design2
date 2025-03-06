#!/usr/bin/env python3
import unittest
import sys
import os
import csv
import tempfile
import glob
from unittest.mock import patch

# Add the src directory to the path so we can import the modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import archive_logs

class TestArchiveLogs(unittest.TestCase):
    """Test cases for the archive_logs module."""
    
    def setUp(self):
        """Set up a temporary directory structure for testing."""
        # Create temp directories for logs and archives
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = os.path.join(self.temp_dir.name, "logs")
        self.archive_dir = os.path.join(self.temp_dir.name, "archives")
        
        # Create the log directory
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create some test log files
        self.create_test_log_files()
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def create_test_log_files(self):
        """Create some test log files with sample data."""
        # VM 1 log
        with open(os.path.join(self.log_dir, "vm_1.log"), "w") as f:
            f.write("1.234 - Internal event: old clock was 0, now 1.\n")
            f.write("2.345 - Sent message to VM 2: old clock was 1, now 2.\n")
        
        # VM 2 log
        with open(os.path.join(self.log_dir, "vm_2.log"), "w") as f:
            f.write("1.456 - Internal event: old clock was 0, now 1.\n")
            f.write("2.567 - Received message: old clock was 1, incoming was 1, now 2. Queue length: 0\n")
    
    def test_clear_logs(self):
        """Test clearing log files."""
        # Verify log files exist
        log_files = glob.glob(os.path.join(self.log_dir, "*.log"))
        self.assertEqual(len(log_files), 2)
        
        # Clear logs
        archive_logs.clear_logs(log_dir=self.log_dir)
        
        # Verify log files were deleted
        log_files = glob.glob(os.path.join(self.log_dir, "*.log"))
        self.assertEqual(len(log_files), 0)
    
    @patch('time.strftime')
    def test_archive_logs(self, mock_strftime):
        """Test archiving log files to a CSV."""
        # Mock time.strftime to return a predictable timestamp
        mock_strftime.return_value = "20250305-120000"
        
        # Archive logs
        archive_logs.archive_logs(
            log_dir=self.log_dir,
            archive_dir=self.archive_dir,
            archive_filename_prefix="test_archive"
        )
        
        # Verify archive directory was created
        self.assertTrue(os.path.exists(self.archive_dir))
        
        # Verify archive file was created
        archive_files = glob.glob(os.path.join(self.archive_dir, "*.csv"))
        self.assertEqual(len(archive_files), 1)
        
        # Verify archive filename
        expected_filename = "test_archive_20250305-120000.csv"
        self.assertEqual(os.path.basename(archive_files[0]), expected_filename)
        
        # Verify CSV contents
        with open(archive_files[0], "r", newline="") as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
        
        # Check header row
        self.assertEqual(rows[0], ["Timestamp", "Event", "VM_ID"])
        
        # Check that all log entries were archived (4 entries + 1 header row)
        self.assertEqual(len(rows), 5)
        
        # Check that VM IDs were correctly extracted and included
        vm1_rows = [row for row in rows[1:] if row[2] == "1"]
        vm2_rows = [row for row in rows[1:] if row[2] == "2"]
        self.assertEqual(len(vm1_rows), 2)
        self.assertEqual(len(vm2_rows), 2)
    
    def test_archive_logs_no_files(self):
        """Test archiving logs when there are no log files."""
        # Clear logs first
        archive_logs.clear_logs(log_dir=self.log_dir)
        
        # Archive logs (should not create a CSV)
        archive_logs.archive_logs(
            log_dir=self.log_dir,
            archive_dir=self.archive_dir,
            archive_filename_prefix="test_archive"
        )
        
        # Verify archive directory was created
        self.assertTrue(os.path.exists(self.archive_dir))
        
        # Verify no archive file was created
        archive_files = glob.glob(os.path.join(self.archive_dir, "*.csv"))
        self.assertEqual(len(archive_files), 0)
    
    def test_parse_log_file(self):
        """Test parsing a log file with a hard-coded example."""
        # Here we assume that archive_logs.py now has a helper function named parse_log_file.
        test_log_content = (
            "1.000 - Internal event: old clock was 0, now 1.\n"
            "2.000 - Sent message to VM 2: old clock was 1, now 2.\n"
        )
        # Create a temporary log file with the hard-coded content.
        temp_log_path = os.path.join(self.log_dir, "vm_99.log")
        with open(temp_log_path, "w") as f:
            f.write(test_log_content)
        
        # Use the helper function to parse the file.
        rows = archive_logs.parse_log_file(temp_log_path)
        
        # Define the expected output.
        expected = [
            ["1.000", "Internal event: old clock was 0, now 1.", "99"],
            ["2.000", "Sent message to VM 2: old clock was 1, now 2.", "99"]
        ]
        self.assertEqual(rows, expected)

# Custom test runner for colored output when this file is run directly.
if __name__ == "__main__":
    # ANSI escape codes for colors.
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
