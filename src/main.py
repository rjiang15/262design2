# src/main.py

import time
import threading
from virtual_machine import VirtualMachine

def run_vm(vm, stop_event):
    """Run the virtual machine event loop based on its tick rate until a stop signal is received."""
    tick_interval = 1.0 / vm.tick_rate
    while not stop_event.is_set():
        vm.run_tick()
        time.sleep(tick_interval)

if __name__ == "__main__":
    # Create a shutdown event
    stop_event = threading.Event()

    # Initialize three virtual machines.
    vm1 = VirtualMachine(vm_id=1)
    vm2 = VirtualMachine(vm_id=2)
    vm3 = VirtualMachine(vm_id=3)
    vms = [vm1, vm2, vm3]
    
    # Set peers for each VM.
    for vm in vms:
        vm.set_peers(vms)
    
    # Start each VM's event loop in its own thread.
    threads = []
    for vm in vms:
        t = threading.Thread(target=run_vm, args=(vm, stop_event), daemon=True)
        t.start()
        threads.append(t)
    
    # Keep the main thread alive until a KeyboardInterrupt.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutdown signal received. Stopping simulation...")
        stop_event.set()
        for t in threads:
            t.join()
        # Shutdown each VM to close log files.
        for vm in vms:
            vm.shutdown()
        print("Simulation terminated gracefully.")
