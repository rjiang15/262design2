#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import argparse
import subprocess
from archive_logs import archive_and_clear_logs

def main():
    # Archive and clear old logs before starting a new experiment.
    archive_and_clear_logs()

    parser = argparse.ArgumentParser(description="Manager script that spawns multiple VM processes.")
    parser.add_argument("--num_vms", type=int, default=3, 
                        help="Number of virtual machines (default: 3)")
    parser.add_argument("--duration", type=int, default=60, 
                        help="Simulation duration in seconds (default: 60)")
    parser.add_argument("--base_port", type=int, default=5000,
                        help="Base port for networking. Each VM listens on base_port + vm_id.")
    parser.add_argument("--tick_rates", type=str, default="",
                        help="Comma-separated list of tick rates for each VM (e.g. '1,5,10'). If fewer than num_vms, reuse in a cycle.")
    parser.add_argument("--send_threshold", type=int, default=3,
                        help="If random event <= this threshold, send messages. Otherwise internal event.")
    args = parser.parse_args()

    # Parse tick rates if provided, otherwise default to random or some fallback
    if args.tick_rates:
        rates = [float(x.strip()) for x in args.tick_rates.split(",")]
    else:
        rates = [1.0] * args.num_vms  # fallback if no tick rates specified

    processes = []
    try:
        # Spawn each VM as a separate process running run_vm.py
        for i in range(args.num_vms):
            vm_id = i + 1
            tick_rate = rates[i % len(rates)]

            cmd = [
                sys.executable,                # e.g. /usr/bin/python3
                os.path.join(os.path.dirname(__file__), "run_vm.py"),  # path to run_vm.py (adjust if needed)
                "--vm_id", str(vm_id),
                "--tick_rate", str(tick_rate),
                "--base_port", str(args.base_port),
                "--duration", str(args.duration),
                "--send_threshold", str(args.send_threshold)
            ]
            print(f"Starting VM {vm_id} with tick_rate={tick_rate}")
            p = subprocess.Popen(cmd)
            processes.append(p)

        # Wait for all processes to finish
        for p in processes:
            p.wait()

    except KeyboardInterrupt:
        print("Keyboard interrupt received. Terminating all VM processes.")
        for p in processes:
            p.terminate()
    finally:
        print("All VMs have stopped. Simulation complete.")

if __name__ == "__main__":
    main()
