# src/virtual_machine.py

import os
import random
import time
import json
from logical_clock import LogicalClock
from network import start_server, connect_to_peer

class VirtualMachine:
    def __init__(self, vm_id, tick_rate=None, tick_min=1, tick_max=6, send_threshold=3):
        """
        Initialize a virtual machine.

        Args:
            vm_id (int): Unique identifier.
            tick_rate (float, optional): The real-time ticks per second.
            tick_min (int): Minimum tick rate if none is specified.
            tick_max (int): Maximum tick rate if none is specified.
            send_threshold (int): If random event <= this threshold => attempt to send messages,
                                  else => internal event.
        """
        self.vm_id = vm_id
        self.tick_min = tick_min
        self.tick_max = tick_max
        self.send_threshold = send_threshold
        self.tick_rate = tick_rate if tick_rate is not None else random.randint(tick_min, tick_max)

        # Create a logical clock (Lamport-based)
        self.clock = LogicalClock()

        # Incoming message queue
        self.msg_queue = []

        # List of peers (by ID or object)
        self.peers = []
        # Sockets keyed by peer VM ID
        self.peer_sockets = {}

        # Network attributes
        self.server_socket = None  # Listening socket from start_server()

        # Logging setup
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = open(os.path.join(log_dir, f"vm_{self.vm_id}.log"), "w")

        # Log VM parameters
        self.log_event(f"PARAMETERS: tick_rate = {self.tick_rate}, send_threshold = {self.send_threshold}")

    def log_event(self, event_str):
        """Write a timestamped event line to the VM's log file (and print)."""
        timestamp = time.perf_counter()
        log_entry = f"{timestamp:.3f} - {event_str}\n"
        self.log_file.write(log_entry)
        self.log_file.flush()
        print(f"VM {self.vm_id}: {log_entry.strip()}")

    def start_network(self):
        """
        Start a server socket for this VM to accept connections
        from peers (multi-process mode).
        """
        start_server(self)

    def set_peers(self, peers):
        """
        Set references to peer VMs (intra-process) or IDs (multi-process).
        Then connect sockets for each peer if possible.
        """
        self.peers = [p for p in peers if p != self.vm_id]
        for pid in self.peers:
            sock = connect_to_peer(self, pid)
            if sock:
                self.peer_sockets[pid] = sock

    def set_peers_from_config(self, peer_ids, host="127.0.0.1", base_port=5000):
        """
        Multi-process mode: connect to each peer by ID and store the socket.
        """
        self.peers = []
        for pid in peer_ids:
            if pid == self.vm_id:
                continue
            sock = connect_to_peer(self, pid, host=host, base_port=base_port)
            if sock:
                self.peer_sockets[pid] = sock
                self.peers.append(pid)

    def process_message(self, message):
        """
        Process a single message from the queue:
          - local_clock = max(local_clock, message["clock"]) + 1
        """
        old_clock = self.clock.get_time()
        incoming_clock = message.get('clock', 0)
        new_clock = self.clock.update(incoming_clock)
        self.log_event(
            f"Received message: old clock was {old_clock}, incoming was {incoming_clock}, now {new_clock}. "
            f"Queue length: {len(self.msg_queue)}"
        )

    def internal_event(self):
        """Perform an internal event => increment local clock, then log."""
        old_clock = self.clock.get_time()
        new_clock = self.clock.tick()
        self.log_event(f"Internal event: old clock was {old_clock}, now {new_clock}.")

    def send_message(self, target_vm, message):
        """
        Send a message (intra-process style). We attach the old clock value,
        then increment locally, then log the new clock.
        """
        old_clock = self.clock.get_time()
        message['clock'] = old_clock

        sock = self.peer_sockets.get(target_vm.vm_id)
        msg_json = json.dumps(message) + "\n"

        if sock:
            try:
                sock.sendall(msg_json.encode("utf-8"))
                new_clock = self.clock.tick()
                self.log_event(
                    f"Sent message to VM {target_vm.vm_id}: old clock was {old_clock}, now {new_clock}."
                )
            except Exception as e:
                self.log_event(f"Network send error to VM {target_vm.vm_id}: {e}")
        else:
            # Direct call if no socket
            target_vm.receive_message(message)
            new_clock = self.clock.tick()
            self.log_event(
                f"Sent message directly to VM {target_vm.vm_id}: old clock was {old_clock}, now {new_clock}."
            )

    def send_message_by_id(self, peer_id, message):
        """
        Send a message (multi-process style) by peer ID.
        Attach old clock, increment, then log.
        """
        old_clock = self.clock.get_time()
        message['clock'] = old_clock
        msg_json = json.dumps(message) + "\n"

        sock = self.peer_sockets.get(peer_id)
        if sock:
            try:
                sock.sendall(msg_json.encode("utf-8"))
                new_clock = self.clock.tick()
                self.log_event(
                    f"Sent message to VM {peer_id}: old clock was {old_clock}, now {new_clock}."
                )
            except Exception as e:
                self.log_event(f"Network send error to VM {peer_id}: {e}")
                # Even on error, we do a local tick
                new_clock = self.clock.tick()
                self.log_event(
                    f"Local clock increment after failed send: old clock was {old_clock}, now {new_clock}."
                )
        else:
            # No connection => can't send
            self.log_event(f"No connection to VM {peer_id}, message not sent.")
            new_clock = self.clock.tick()
            self.log_event(
                f"Local clock increment after failed send: old clock was {old_clock}, now {new_clock}."
            )

    def receive_message(self, message):
        """Enqueue a message for run_tick() to process on the next iteration."""
        self.msg_queue.append(message)

    def run_tick(self):
        """
        Perform one “tick” of the VM’s logic:
          - If there is a queued message, process it.
          - Otherwise, pick a random event: send or internal event.
        """
        if self.msg_queue:
            msg = self.msg_queue.pop(0)
            self.process_message(msg)
        else:
            event_choice = random.randint(1, self.send_threshold)
            if event_choice == 1 and self.peers:
                first = self.peers[0]
                if isinstance(first, int):
                    self.send_message_by_id(first, {})
                else:
                    self.send_message(first, {})
            elif event_choice == 2 and len(self.peers) >= 2:
                second = self.peers[1]
                if isinstance(second, int):
                    self.send_message_by_id(second, {})
                else:
                    self.send_message(second, {})
            elif event_choice == 3 and self.peers:
                for p in self.peers:
                    if isinstance(p, int):
                        self.send_message_by_id(p, {})
                    else:
                        self.send_message(p, {})
            else:
                self.internal_event()

    def shutdown(self):
        """Clean up resources."""
        if self.server_socket:
            self.server_socket.close()
        for sock in self.peer_sockets.values():
            try:
                sock.close()
            except:
                pass
        self.log_file.close()

if __name__ == "__main__":
    # Simple test for a single VM
    vm = VirtualMachine(vm_id=1, tick_rate=1)
    vm.start_network()
    print(f"VM {vm.vm_id} started with tick_rate={vm.tick_rate}.")
    vm.run_tick()
