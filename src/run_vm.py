#!/usr/bin/env python3

import sys
import os
import time
import argparse
from virtual_machine import VirtualMachine

def run_vm_worker(vm_id, tick_rate, base_port, duration, send_threshold, total_vms):
    """
    Create a VM, set up networking, and run its event loop for the given duration.
    """
    # Create the VirtualMachine instance
    vm = VirtualMachine(
        vm_id=vm_id,
        tick_rate=tick_rate,
        send_threshold=send_threshold
    )

    # Start the network listener
    vm.start_network()  # This uses the default host="127.0.0.1" & base_port logic in network.py

    # Set peers from total_vms (multi-process mode)
    peer_ids = [i for i in range(1, total_vms + 1) if i != vm_id]
    vm.set_peers_from_config(peer_ids, host="127.0.0.1", base_port=base_port)

    print(f"VM {vm_id} started with tick_rate={vm.tick_rate} in process PID {os.getpid()}")

    # Use perf_counter for high-resolution timing
    start_time = time.perf_counter()
    interval = 1.0 / vm.tick_rate  # Fixed interval per tick
    next_time = start_time + interval

    # Run the event loop until the simulation duration expires
    while time.perf_counter() - start_time < duration:
        now = time.perf_counter()
        if now >= next_time:
            vm.run_tick()
            next_time += interval
        else:
            # Sleep only as long as needed until the next tick.
            time.sleep(max(0, next_time - now))

    vm.shutdown()
    print(f"VM {vm_id} finished after {duration} seconds.")


def main():
    parser = argparse.ArgumentParser(description="Run a single Virtual Machine in a separate process.")
    parser.add_argument("--vm_id", type=int, required=True, help="Unique ID for this VM.")
    parser.add_argument("--tick_rate", type=float, required=True, help="Tick rate for this VM.")
    parser.add_argument("--base_port", type=int, default=5000, help="Base port for networking.")
    parser.add_argument("--duration", type=int, default=60, help="Duration to run (in seconds).")
    parser.add_argument("--send_threshold", type=int, default=3, help="Send threshold for events.")
    parser.add_argument("--total_vms", type=int, required=True, help="Total number of VMs in the simulation.")
    args = parser.parse_args()

    run_vm_worker(
        vm_id=args.vm_id,
        tick_rate=args.tick_rate,
        base_port=args.base_port,
        duration=args.duration,
        send_threshold=args.send_threshold,
        total_vms=args.total_vms
    )

if __name__ == "__main__":
    main()
