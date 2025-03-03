#!/usr/bin/env python3

import sys
import os
import time
import argparse
from virtual_machine import VirtualMachine

def run_vm():
    parser = argparse.ArgumentParser(description="Run a single Virtual Machine as a separate process.")
    parser.add_argument("--vm_id", type=int, required=True, 
                        help="Unique ID for this VM.")
    parser.add_argument("--tick_rate", type=float, required=True,
                        help="Number of ticks per second for this VM.")
    parser.add_argument("--base_port", type=int, default=5000,
                        help="Base port for networking. The VM will listen on base_port + vm_id.")
    parser.add_argument("--send_threshold", type=int, default=3,
                        help="If random event <= this threshold, send messages. Otherwise internal event.")
    parser.add_argument("--duration", type=int, default=60,
                        help="How long (in seconds) this VM should run before shutting down.")
    args = parser.parse_args()

    # Create the VirtualMachine instance.
    vm = VirtualMachine(
        vm_id=args.vm_id,
        tick_rate=args.tick_rate,
        send_threshold=args.send_threshold
    )

    # Print the current process ID to verify separate address spaces.
    print(f"VM {args.vm_id} running in process with PID: {os.getpid()}")

    # Start the network listener with the provided host and base_port.
    vm.start_network(host="127.0.0.1", base_port=args.base_port)

    # Run the event loop for the specified duration.
    start_time = time.time()
    while time.time() - start_time < args.duration:
        vm.run_tick()
        time.sleep(1.0 / vm.tick_rate)

    vm.shutdown()
    print(f"VM {args.vm_id} finished after {args.duration} seconds.")

if __name__ == "__main__":
    run_vm()
