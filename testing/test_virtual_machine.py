#!/usr/bin/env python3
import unittest
import sys
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

# Add the src directory to the path so we can import the modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from virtual_machine import VirtualMachine
from logical_clock import LogicalClock

class TestVirtualMachine(unittest.TestCase):
    """Test cases for the VirtualMachine class."""
    
    def setUp(self):
        """Set up a temporary directory for log files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        
        # Patch os.path.join to redirect log files to our temp directory
        self.original_join = os.path.join
        os.path.join = lambda *args: self.temp_dir.name if args[-2:] == ('..', 'logs') else self.original_join(*args)

    def tearDown(self):
        """Clean up after tests."""
        # Restore original os.path.join
        os.path.join = self.original_join
        self.temp_dir.cleanup()
    
    def test_init(self):
        """Test initialization with default and custom values."""
        # Test with default values
        vm = VirtualMachine(vm_id=1)
        self.assertEqual(vm.vm_id, 1)
        self.assertIsInstance(vm.clock, LogicalClock)
        self.assertEqual(vm.clock.get_time(), 0)
        self.assertEqual(vm.msg_queue, [])
        self.assertEqual(vm.peers, [])
        self.assertEqual(vm.peer_sockets, {})
        
        # Test with custom values
        vm = VirtualMachine(vm_id=2, tick_rate=10, tick_min=2, tick_max=20, send_threshold=5)
        self.assertEqual(vm.vm_id, 2)
        self.assertEqual(vm.tick_rate, 10)
        self.assertEqual(vm.tick_min, 2)
        self.assertEqual(vm.tick_max, 20)
        self.assertEqual(vm.send_threshold, 5)
    
    def test_log_event(self):
        """Test logging events to file."""
        vm = VirtualMachine(vm_id=3)
        vm.log_event("Test event")
        
        # Check that the log file was created and contains the event
        log_path = os.path.join(self.temp_dir.name, f"vm_{vm.vm_id}.log")
        self.assertTrue(os.path.exists(log_path))
        
        with open(log_path, 'r') as f:
            log_content = f.read()
        
        self.assertIn("Test event", log_content)
    
    def test_receive_and_process_message(self):
        """Test receiving and processing a message."""
        vm = VirtualMachine(vm_id=4)
        
        # Set up initial clock state
        vm.clock.time = 5
        
        # Receive a message
        message = {'clock': 10}
        vm.receive_message(message)
        
        # Check that the message was added to the queue
        self.assertEqual(len(vm.msg_queue), 1)
        self.assertEqual(vm.msg_queue[0], message)
        
        # Process the message
        vm.process_message(message)
        
        # Check that the clock was updated correctly (max(5, 10) + 1 = 11)
        self.assertEqual(vm.clock.get_time(), 11)
    
    def test_internal_event(self):
        """Test internal event execution."""
        vm = VirtualMachine(vm_id=5)
        
        # Set up initial clock state
        vm.clock.time = 7
        
        # Execute internal event
        vm.internal_event()
        
        # Check that the clock was incremented
        self.assertEqual(vm.clock.get_time(), 8)
    
    @patch('virtual_machine.connect_to_peer')
    def test_set_peers_from_config(self, mock_connect):
        """Test setting peers from configuration."""
        # Mock the connect_to_peer function to return a socket
        mock_socket = MagicMock()
        mock_connect.return_value = mock_socket
        
        vm = VirtualMachine(vm_id=6)
        vm.set_peers_from_config([1, 2, 3, 6, 7, 8])
        
        # Should not connect to itself (vm_id=6)
        self.assertEqual(len(vm.peers), 5)
        self.assertNotIn(6, vm.peers)
        self.assertIn(1, vm.peers)
        self.assertIn(2, vm.peers)
        self.assertIn(3, vm.peers)
        self.assertIn(7, vm.peers)
        self.assertIn(8, vm.peers)
        
        # Check that sockets were stored for each peer
        self.assertEqual(len(vm.peer_sockets), 5)
        self.assertEqual(vm.peer_sockets[1], mock_socket)
        self.assertEqual(vm.peer_sockets[2], mock_socket)
        self.assertEqual(vm.peer_sockets[3], mock_socket)
        self.assertEqual(vm.peer_sockets[7], mock_socket)
        self.assertEqual(vm.peer_sockets[8], mock_socket)
    
    def test_run_tick_with_queued_message(self):
        """Test run_tick when there's a message in the queue."""
        vm = VirtualMachine(vm_id=7)
        
        # Set up initial clock state
        vm.clock.time = 3
        
        # Add a message to the queue
        message = {'clock': 5}
        vm.msg_queue.append(message)
        
        # Run a tick
        vm.run_tick()
        
        # Check that the message was processed and the clock was updated
        self.assertEqual(len(vm.msg_queue), 0)  # Queue should be empty now
        self.assertEqual(vm.clock.get_time(), 6)  # max(3, 5) + 1 = 6
    
    @patch('random.randint')
    @patch('virtual_machine.VirtualMachine.send_message_by_id')
    def test_run_tick_send_to_first_peer(self, mock_send, mock_randint):
        """Test run_tick when it sends a message to the first peer."""
        # Mock random choice to always choose event 1 (send to first peer)
        mock_randint.return_value = 1
        
        vm = VirtualMachine(vm_id=8, send_threshold=5)
        vm.peers = [10, 11]  # Add some peer IDs
        
        # Run a tick
        vm.run_tick()
        
        # Check that send_message_by_id was called for the first peer
        mock_send.assert_called_once_with(10, {})

    @patch('random.randint')
    def test_run_tick_internal_event(self, mock_randint):
        """Test run_tick when it performs an internal event."""
        # Mock random choice to choose an event above the threshold
        mock_randint.return_value = 5
        
        vm = VirtualMachine(vm_id=9, send_threshold=3)
        vm.peers = [12, 13]  # Add some peer IDs
        
        # Set up initial clock state
        vm.clock.time = 9
        
        # Run a tick
        vm.run_tick()
        
        # Check that the clock was incremented (internal event)
        self.assertEqual(vm.clock.get_time(), 10)
    
    def test_shutdown(self):
        """Test proper resource cleanup during shutdown."""
        vm = VirtualMachine(vm_id=10)
        
        # Mock server socket and peer sockets
        vm.server_socket = MagicMock()
        vm.peer_sockets = {1: MagicMock(), 2: MagicMock()}
        
        # Call shutdown
        vm.shutdown()
        
        # Check that all sockets were closed
        vm.server_socket.close.assert_called_once()
        vm.peer_sockets[1].close.assert_called_once()
        vm.peer_sockets[2].close.assert_called_once()

if __name__ == "__main__":
    unittest.main()