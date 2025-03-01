# src/main.py

import time
import threading
import argparse
from virtual_machine import VirtualMachine

def run_vm(vm, stop_event):
    """Run the VM's event loop until stop_event is set."""
    tick_interval = 1.0 / vm.tick_rate
    while not stop_event.is_set():
        vm.run_tick()
        time.sleep(tick_interval)

def main():
    # Set up command-line arguments.
    parser = argparse.ArgumentParser(description="Distributed System Simulation")
    parser.add_argument("--num_vms", type=int, default=3, 
                        help="Number of virtual machines in the simulation (default: 3)")
    parser.add_argument("--duration", type=int, default=60, 
                        help="Simulation duration in seconds (default: 60)")
    # Additional parameters (like base port, probability distributions, etc.) can be added here.
    args = parser.parse_args()

    # Create the specified number of VMs.
    num_vms = args.num_vms
    vms = [VirtualMachine(vm_id=i+1) for i in range(num_vms)]

    # Start network listeners for each VM.
    for vm in vms:
        vm.start_network()

    # Connect each VM to its peers.
    for vm in vms:
        vm.set_peers(vms)

    stop_event = threading.Event()
    threads = []
    for vm in vms:
        t = threading.Thread(target=run_vm, args=(vm, stop_event), daemon=True)
        t.start()
        threads.append(t)

    # Run the simulation for the specified duration.
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
