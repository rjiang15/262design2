# src/virtual_machine.py

import os
import random
import time
import json
import threading
from logical_clock import LogicalClock
from network import start_server, connect_to_peer

class VirtualMachine:
    def __init__(self, vm_id, tick_rate=None, tick_min=1, tick_max=6, send_threshold=3):
        """
        Initialize a virtual machine.
        
        Args:
            vm_id (int): Unique identifier.
            tick_rate (float, optional): If provided, this tick rate is used.
            tick_min (int): Minimum tick rate.
            tick_max (int): Maximum tick rate.
            send_threshold (int): If a random event's value is <= this, send messages.
        """
        self.vm_id = vm_id
        self.tick_min = tick_min
        self.tick_max = tick_max
        self.send_threshold = send_threshold
        self.tick_rate = tick_rate if tick_rate is not None else random.randint(tick_min, tick_max)
        self.clock = LogicalClock()
        self.msg_queue = []
        self.peers = []  # Other VirtualMachine instances
        self.peer_sockets = {}  # Map: peer vm_id -> socket

        # Network attributes.
        self.server_socket = None
        self.network_thread = None
        self.network_stop_event = threading.Event()

        # Ensure logs directory exists.
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_file = open(os.path.join(log_dir, f"vm_{self.vm_id}.log"), "w")

    def set_peers(self, peers):
        """Set peers and establish network connections."""
        self.peers = [peer for peer in peers if peer.vm_id != self.vm_id]
        for peer in self.peers:
            sock = connect_to_peer(self, peer.vm_id)
            if sock:
                self.peer_sockets[peer.vm_id] = sock

    def start_network(self, host="127.0.0.1", base_port=5000):
        """Start network listener with given host and base port."""
        start_server(self, host=host, base_port=base_port)

    def log_event(self, event_str):
        timestamp = time.time()
        log_entry = f"{timestamp:.3f} - {event_str}\n"
        self.log_file.write(log_entry)
        self.log_file.flush()
        print(f"VM {self.vm_id}: {log_entry.strip()}")

    def process_message(self, message):
        """Process incoming message."""
        received_clock = message.get('clock', 0)
        new_clock = self.clock.update(received_clock)
        self.log_event(f"Received message: updated clock to {new_clock}. Queue length: {len(self.msg_queue)}")

    def internal_event(self):
        """Process an internal event."""
        new_clock = self.clock.tick()
        self.log_event(f"Internal event: clock ticked to {new_clock}.")

    def send_message(self, target_vm, message):
        """Send message over the network."""
        new_clock = self.clock.tick()
        message['clock'] = new_clock
        message_json = json.dumps(message) + "\n"
        sock = self.peer_sockets.get(target_vm.vm_id)
        if sock:
            try:
                sock.sendall(message_json.encode("utf-8"))
                self.log_event(f"Sent message to VM {target_vm.vm_id}: clock is now {new_clock}.")
            except Exception as e:
                self.log_event(f"Network send error to VM {target_vm.vm_id}: {e}")
        else:
            target_vm.receive_message(message)
            self.log_event(f"Sent message directly to VM {target_vm.vm_id}: clock is now {new_clock}.")

    def receive_message(self, message):
        """Enqueue received message."""
        self.msg_queue.append(message)

    def run_tick(self):
        """
        Simulate one tick:
         - Process one queued message if available.
         - Otherwise, generate a random number (1-10).
           If <= send_threshold, then:
             * 1: send to first peer.
             * 2: send to second peer (if available).
             * 3: send to all peers.
           Else, process an internal event.
        """
        if self.msg_queue:
            message = self.msg_queue.pop(0)
            self.process_message(message)
        else:
            event_choice = random.randint(1, 10)
            if event_choice <= self.send_threshold:
                if event_choice == 1 and self.peers:
                    self.send_message(self.peers[0], {'clock': 0})
                elif event_choice == 2 and len(self.peers) >= 2:
                    self.send_message(self.peers[1], {'clock': 0})
                elif event_choice == 3 and self.peers:
                    for peer in self.peers:
                        self.send_message(peer, {'clock': 0})
                else:
                    self.internal_event()
            else:
                self.internal_event()

    def shutdown(self):
        """Clean up resources."""
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
    # Simple network test for a single VM.
    vm = VirtualMachine(vm_id=1)
    vm.set_peers([])
    vm.start_network()  # Will use default host and base_port.
    print(f"VM {vm.vm_id} initialized with tick rate: {vm.tick_rate} ticks per second.")
    vm.run_tick()
