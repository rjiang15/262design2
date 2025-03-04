#!/usr/bin/env python3

import sys
import os
import time
import argparse
from virtual_machine import VirtualMachine

def run_vm_worker(vm_id, tick_rate, base_port, duration, send_threshold, total_vms):
    # Create the VirtualMachine instance.
    vm = VirtualMachine(
        vm_id=vm_id,
        tick_rate=tick_rate,
        send_threshold=send_threshold
    )

    # Start the network listener.
    vm.start_network()  # Uses default host="127.0.0.1" and BASE_PORT logic in network.py

    # Compute peer IDs from the total number of VMs.
    peer_ids = [i for i in range(1, total_vms + 1) if i != vm_id]
    vm.set_peers_from_config(peer_ids, host="127.0.0.1", base_port=base_port)

    # Print the process ID for verification.
    print(f"VM {vm_id} started with tick_rate={vm.tick_rate} in process PID {os.getpid()}")

    # Run the event loop in real time.
    start_time = time.time()
    while time.time() - start_time < duration:
        vm.run_tick()
        time.sleep(1.0 / vm.tick_rate)

    vm.shutdown()
    print(f"VM {vm_id} finished after {duration} seconds.")

def main():
    parser = argparse.ArgumentParser(description="Run a single Virtual Machine in a separate process.")
    parser.add_argument("--vm_id", type=int, required=True, help="Unique ID for this VM.")
    parser.add_argument("--tick_rate", type=float, required=True, help="Tick rate for this VM.")
    parser.add_argument("--base_port", type=int, default=5000, help="Base port for networking.")
    parser.add_argument("--duration", type=int, default=60, help="Duration to run (seconds).")
    parser.add_argument("--send_threshold", type=int, default=3, help="Send threshold for events.")
    parser.add_argument("--total_vms", type=int, required=True, help="Total number of VMs in the simulation.")
    args = parser.parse_args()
    run_vm_worker(args.vm_id, args.tick_rate, args.base_port, args.duration, args.send_threshold, args.total_vms)

if __name__ == "__main__":
    main()
