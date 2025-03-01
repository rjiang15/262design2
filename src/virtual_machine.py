# src/virtual_machine.py

import os
import random
import time
from logical_clock import LogicalClock

class VirtualMachine:
    def __init__(self, vm_id, tick_rate=None):
        """
        Initialize a virtual machine.
        
        Args:
            vm_id (int): Unique identifier for the virtual machine.
            tick_rate (int, optional): Number of clock ticks per second. If not provided,
                                       a random value between 1 and 6 is chosen.
        """
        self.vm_id = vm_id
        self.tick_rate = tick_rate if tick_rate is not None else random.randint(1, 6)
        self.clock = LogicalClock()
        self.msg_queue = []
        self.peers = []  # List of other VirtualMachine instances

        # Ensure the logs directory exists.
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        self.log_file = open(os.path.join(log_dir, f"vm_{self.vm_id}.log"), "w")

    def set_peers(self, peers):
        """
        Set the list of peer VMs.
        """
        # Exclude self from peers if present.
        self.peers = [peer for peer in peers if peer.vm_id != self.vm_id]

    def log_event(self, event_str):
        """Log an event with a timestamp."""
        timestamp = time.time()  # System time
        log_entry = f"{timestamp:.3f} - {event_str}\n"
        self.log_file.write(log_entry)
        self.log_file.flush()
        print(f"VM {self.vm_id}: {log_entry.strip()}")

    def process_message(self, message):
        """
        Process an incoming message.
        
        The message is assumed to be a dict containing a 'clock' key.
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
        Send a message to another virtual machine.
        
        The method ticks the local logical clock, attaches the clock value to the message,
        and directly calls the target's receive_message method.
        """
        new_clock = self.clock.tick()
        message['clock'] = new_clock
        target_vm.receive_message(message)
        self.log_event(f"Sent message to VM {target_vm.vm_id}: clock is now {new_clock}.")

    def receive_message(self, message):
        """Receive a message by adding it to the message queue."""
        self.msg_queue.append(message)

    def run_tick(self):
        """
        Simulate one tick of the VM.
        
        - If there is a message in the queue, process one message.
        - Otherwise, generate a random event:
            - If random value is 1: send message to the first peer.
            - If random value is 2: send message to the second peer (if available).
            - If random value is 3: send message to all peers.
            - Otherwise (4-10): process an internal event.
        """
        if self.msg_queue:
            message = self.msg_queue.pop(0)
            self.process_message(message)
        else:
            event_choice = random.randint(1, 10)
            if event_choice == 1 and self.peers:
                # Send message to first peer
                self.send_message(self.peers[0], {'clock': 0})
            elif event_choice == 2 and len(self.peers) >= 2:
                # Send message to second peer
                self.send_message(self.peers[1], {'clock': 0})
            elif event_choice == 3 and self.peers:
                # Send message to all peers
                for peer in self.peers:
                    self.send_message(peer, {'clock': 0})
            else:
                self.internal_event()

    def shutdown(self):
        """Clean up resources, such as closing the log file."""
        self.log_file.close()

if __name__ == "__main__":
    # Simple test of the VirtualMachine functionality in isolation.
    vm = VirtualMachine(vm_id=1)
    # For testing, set an empty peers list (or add dummy peers).
    vm.set_peers([])
    print(f"VM {vm.vm_id} initialized with tick rate: {vm.tick_rate} ticks per second.")
    vm.run_tick()
