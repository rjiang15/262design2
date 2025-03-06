#!/usr/bin/env python3
import unittest
import sys
import os
import socket
import threading
import time
from unittest.mock import patch, MagicMock, call

# Add the src directory to the path so we can import the modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import network

class TestNetwork(unittest.TestCase):
    """Test cases for the network module."""
    
    def setUp(self):
        """Set up for tests."""
        # Create a mock VM for tests
        self.mock_vm = MagicMock()
        self.mock_vm.vm_id = 1
        self.mock_vm.log_event = MagicMock()
    
    @patch('socket.socket')
    def test_connect_to_peer_success(self, mock_socket):
        """Test connecting to a peer successfully."""
        # Set up the mock socket
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket
        
        # Test connecting to peer ID 2
        peer_id = 2
        result = network.connect_to_peer(self.mock_vm, peer_id)
        
        # Check that socket was created and connected correctly
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_client_socket.connect.assert_called_once_with(('127.0.0.1', network.BASE_PORT + peer_id))
        
        # Check that log_event was called
        self.mock_vm.log_event.assert_called_once()
        
        # Check that the function returned the socket
        self.assertEqual(result, mock_client_socket)
    
    @patch('socket.socket')
    @patch('time.sleep')
    def test_connect_to_peer_retry(self, mock_sleep, mock_socket):
        """Test retrying connection to a peer."""
        # Set up the mock socket to raise ConnectionRefusedError on first attempt
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket
        mock_client_socket.connect.side_effect = [ConnectionRefusedError, None]
        
        # Test connecting to peer ID 3 with retry
        peer_id = 3
        result = network.connect_to_peer(self.mock_vm, peer_id, max_retries=2)
        
        # Check that socket was created twice and connect was called twice
        self.assertEqual(mock_socket.call_count, 2)
        mock_client_socket.connect.assert_has_calls([
            call(('127.0.0.1', network.BASE_PORT + peer_id)),
            call(('127.0.0.1', network.BASE_PORT + peer_id))
        ])
        
        # Check that sleep was called once for the retry
        mock_sleep.assert_called_once_with(1)
        
        # Check that log_event was called
        self.mock_vm.log_event.assert_called_once()
        
        # Check that the function returned the socket
        self.assertEqual(result, mock_client_socket)
    
    @patch('socket.socket')
    def test_connect_to_peer_failure(self, mock_socket):
        """Test failing to connect to a peer after max retries."""
        # Set up the mock socket to always raise ConnectionRefusedError
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket
        mock_client_socket.connect.side_effect = ConnectionRefusedError
        
        # Test connecting to peer ID 4 with max_retries=1
        peer_id = 4
        result = network.connect_to_peer(self.mock_vm, peer_id, max_retries=1)
        
        # Check that socket was created and connect was called
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_client_socket.connect.assert_called_once_with(('127.0.0.1', network.BASE_PORT + peer_id))
        
        # Check that the function returned None
        self.assertIsNone(result)
    
    @patch('socket.socket')
    def test_connect_to_peer_exception(self, mock_socket):
        """Test handling other exceptions when connecting to a peer."""
        # Set up the mock socket to raise a generic Exception
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket
        mock_client_socket.connect.side_effect = Exception("Test exception")
        
        # Test connecting to peer ID 5
        peer_id = 5
        result = network.connect_to_peer(self.mock_vm, peer_id)
        
        # Check that socket was created and connect was called
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_client_socket.connect.assert_called_once_with(('127.0.0.1', network.BASE_PORT + peer_id))
        
        # Check that log_event was called
        self.mock_vm.log_event.assert_called_once()
        
        # Check that the function returned None
        self.assertIsNone(result)

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
