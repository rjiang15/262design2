# src/virtual_machine.py

import os
import random
import time
import json
import threading
from logical_clock import LogicalClock
from network import start_server, connect_to_peer

class VirtualMachine:
    def __init__(self, vm_id, tick_rate=None):
        """
        Initialize a virtual machine.
        """
        self.vm_id = vm_id
        self.tick_rate = tick_rate if tick_rate is not None else random.randint(1, 6)
        self.clock = LogicalClock()
        self.msg_queue = []
        self.peers = []  # List of other VirtualMachine instances (for logical purposes)
        self.peer_sockets = {}  # Map: peer vm_id -> socket

        # Network-related attributes
        self.server_socket = None
        self.network_thread = None
        self.network_stop_event = threading.Event()

        # Ensure the logs directory exists.
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_file = open(os.path.join(log_dir, f"vm_{self.vm_id}.log"), "w")

    def set_peers(self, peers):
        """
        Set the list of peer VMs (for simulation logic) and connect to them over the network.
        """
        self.peers = [peer for peer in peers if peer.vm_id != self.vm_id]
        # Establish network connections to each peer.
        for peer in self.peers:
            sock = connect_to_peer(self, peer.vm_id)
            if sock:
                self.peer_sockets[peer.vm_id] = sock

    def start_network(self):
        """Start the network listener."""
        start_server(self)

    def log_event(self, event_str):
        """Log an event with a timestamp."""
        timestamp = time.time()
        log_entry = f"{timestamp:.3f} - {event_str}\n"
        self.log_file.write(log_entry)
        self.log_file.flush()
        print(f"VM {self.vm_id}: {log_entry.strip()}")

    def process_message(self, message):
        """
        Process an incoming message.
        """
        received_clock = message.get('clock', 0)
        new_clock = self.clock.update(received_clock)
        self.log_event(f"Received message: updated clock to {new_clock}. Queue length: {len(self.msg_queue)}")

    def internal_event(self):
        """Process an internal event by ticking the clock."""
        new_clock = self.clock.tick()
        self.log_event(f"Internal event: clock ticked to {new_clock}.")

    def send_message(self, target_vm, message):
        """
        Send a message to another VM over the network.
        """
        new_clock = self.clock.tick()
        message['clock'] = new_clock
        message_json = json.dumps(message) + "\n"
        # Use the network socket if available; otherwise, fall back to direct method call.
        sock = self.peer_sockets.get(target_vm.vm_id)
        if sock:
            try:
                sock.sendall(message_json.encode("utf-8"))
                self.log_event(f"Sent message to VM {target_vm.vm_id}: clock is now {new_clock}.")
            except Exception as e:
                self.log_event(f"Network send error to VM {target_vm.vm_id}: {e}")
        else:
            # Fallback: direct method call (for testing)
            target_vm.receive_message(message)
            self.log_event(f"Sent message directly to VM {target_vm.vm_id}: clock is now {new_clock}.")

    def receive_message(self, message):
        """Receive a message by adding it to the message queue."""
        self.msg_queue.append(message)

    def run_tick(self):
        """
        Simulate one tick of the VM.
        """
        if self.msg_queue:
            message = self.msg_queue.pop(0)
            self.process_message(message)
        else:
            event_choice = random.randint(1, 10)
            if event_choice == 1 and self.peers:
                self.send_message(self.peers[0], {'clock': 0})
            elif event_choice == 2 and len(self.peers) >= 2:
                self.send_message(self.peers[1], {'clock': 0})
            elif event_choice == 3 and self.peers:
                for peer in self.peers:
                    self.send_message(peer, {'clock': 0})
            else:
                self.internal_event()

    def shutdown(self):
        """Clean up resources, close log file and network sockets."""
        self.network_stop_event.set()
        if self.server_socket:
            self.server_socket.close()
        for sock in self.peer_sockets.values():
            try:
                sock.close()
            except:
                pass
        self.log_file.close()

if __name__ == "__main__":
    # Test network functionality in isolation.
    vm = VirtualMachine(vm_id=1)
    vm.set_peers([])  # No peers for isolated test.
    vm.start_network()
    print(f"VM {vm.vm_id} initialized with tick rate: {vm.tick_rate} ticks per second.")
    vm.run_tick()
