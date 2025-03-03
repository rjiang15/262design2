#!/usr/bin/env python3

import sys
import os
# Add project root to the path so we can import archive_logs and other modules.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import threading
import argparse
from virtual_machine import VirtualMachine
from archive_logs import archive_and_clear_logs

def run_vm(vm, stop_event):
    """Run the VM's event loop until stop_event is set."""
    tick_interval = 1.0 / vm.tick_rate
    while not stop_event.is_set():
        vm.run_tick()
        time.sleep(tick_interval)

def main():
    # Archive and clear old logs before starting a new experiment.
    archive_and_clear_logs()

    # Set up command-line arguments.
    parser = argparse.ArgumentParser(description="Distributed System Simulation")
    parser.add_argument("--num_vms", type=int, default=3, 
                        help="Number of virtual machines (default: 3)")
    parser.add_argument("--duration", type=int, default=60, 
                        help="Simulation duration in seconds (default: 60)")
    parser.add_argument("--min_tick", type=float, default=1,
                        help="Minimum tick rate for VMs (default: 1)")
    parser.add_argument("--max_tick", type=float, default=6,
                        help="Maximum tick rate for VMs (default: 6)")
    parser.add_argument("--send_threshold", type=int, default=3,
                        help="If random event <= this threshold, send messages (default: 3)")
    # New flag: comma-separated tick rates for each VM (decimals allowed).
    parser.add_argument("--tick_rates", type=str, default="",
                        help="Comma-separated list of tick rates for each VM (e.g., '0.1,10,100'). If provided, these override min_tick/max_tick.")
    args = parser.parse_args()

    # Determine tick rates for each VM if provided.
    tick_rates = None
    if args.tick_rates:
        try:
            tick_rates = [float(rate.strip()) for rate in args.tick_rates.split(",")]
        except ValueError:
            print("Error: Invalid tick_rates format. Please provide a comma-separated list of numbers.")
            sys.exit(1)
        if len(tick_rates) < args.num_vms:
            print("Warning: Fewer tick rates provided than the number of VMs. Reusing the provided rates cyclically.")

    # Create VMs with either the specified tick rates or random tick rates between min_tick and max_tick.
    vms = []
    import random
    for i in range(args.num_vms):
        if tick_rates:
            tick_rate = tick_rates[i % len(tick_rates)]
        else:
            # Use a random tick rate between min_tick and max_tick.
            tick_rate = random.uniform(args.min_tick, args.max_tick) if args.min_tick != args.max_tick else args.min_tick
        vm = VirtualMachine(vm_id=i+1, tick_rate=tick_rate, 
                            tick_min=args.min_tick, tick_max=args.max_tick, 
                            send_threshold=args.send_threshold)
        vms.append(vm)

    # Start network listeners for each VM.
    for vm in vms:
        vm.start_network()

    # Connect each VM to its peers.
    for vm in vms:
        vm.set_peers(vms)

    # Start each VM's event loop in its own thread.
    stop_event = threading.Event()
    threads = []
    for vm in vms:
        t = threading.Thread(target=run_vm, args=(vm, stop_event), daemon=True)
        t.start()
        threads.append(t)

    # Run simulation for the specified duration.
    try:
        start_time = time.time()
        while time.time() - start_time < args.duration:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt received, shutting down simulation...")
    finally:
        print("Stopping simulation...")
        stop_event.set()
        for t in threads:
            t.join()
        for vm in vms:
            vm.shutdown()
        print("Simulation terminated gracefully.")

if __name__ == "__main__":
    main()
