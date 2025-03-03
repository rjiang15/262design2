#!/usr/bin/env python3

import re
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from matplotlib.patches import Patch

def analyze_logs(csv_file, reference_vm_id=1):
    """
    Reads a CSV log file, parses logical clock data, and generates:
      1) Logical Clock Evolution Over Time
      2) Clock Drift (relative to VM 1)
      3) Message Queue Length Over Time
      4) Event Type Distribution by VM
    Saves each plot as a PNG in a subfolder under outputs/ named 'Graphs of <CSV filename>'.
    """

    # ----------- If csv_file is not an absolute path, assume it is in the archives folder -----------
    if not os.path.isabs(csv_file):
        csv_file = os.path.join("archives", csv_file)
    
    # ----------- Create Output Directory -----------
    base_name = os.path.basename(csv_file)           # e.g. logs_archive_20250302-153306.csv
    file_stem = os.path.splitext(base_name)[0]         # e.g. logs_archive_20250302-153306
    out_dir = os.path.join("outputs", f"Graphs of {file_stem}")
    os.makedirs(out_dir, exist_ok=True)

    # ----------- Load and Prepare Data -----------
    df = pd.read_csv(csv_file)

    # (A) Extract logical clock values from event strings
    def extract_clock(event):
        match = re.search(r"(ticked to|is now) (\d+)", event)
        return int(match.group(2)) if match else None

    df["ClockValue"] = df["Event"].apply(extract_clock)

    # (B) Extract queue length from event strings (for received messages)
    def extract_queue_length(event):
        match = re.search(r"Queue length: (\d+)", event)
        return int(match.group(1)) if match else None

    df["QueueLength"] = df["Event"].apply(extract_queue_length)

    # (C) Categorize events into Internal / Sent / Received / Other
    def categorize_event(event_str):
        if "Internal event" in event_str:
            return "Internal"
        elif "Sent message" in event_str:
            return "Sent"
        elif "Received message" in event_str:
            return "Received"
        else:
            return "Other"

    df["EventType"] = df["Event"].apply(categorize_event)

    # We’ll drop rows without clock values when needed (for clock plots)
    clock_df = df.dropna(subset=["ClockValue"])

    # ----------- Define a Color Map for VMs -----------
    vm_colors = {
        1: "tab:blue",
        2: "tab:orange",
        3: "tab:green",
        4: "tab:red",
        5: "tab:purple",
    }

    # ----------- 1) Logical Clock Evolution Over Time -----------
    plt.figure(figsize=(10, 6))
    for vm_id, group in clock_df.groupby("VM_ID"):
        color = vm_colors.get(vm_id, "gray")
        plt.plot(group["Timestamp"], group["ClockValue"], marker="o", linestyle="-",
                 label=f"VM {vm_id}", color=color)

    plt.xlabel("System Timestamp")
    plt.ylabel("Logical Clock Value")
    plt.title("Logical Clock Evolution Over Time")
    plt.legend()

    # Save the figure
    save_path = os.path.join(out_dir, "01_logical_clock_evolution.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()

    # ----------- 2) Clock Drift Relative to a Reference VM -----------
    ref_data = clock_df[clock_df["VM_ID"] == reference_vm_id].drop_duplicates(subset=["Timestamp"])
    if len(ref_data) < 2:
        print(f"Not enough data for reference VM {reference_vm_id} to perform interpolation.")
    else:
        f_ref = interp1d(ref_data["Timestamp"], ref_data["ClockValue"],
                         bounds_error=False, fill_value="extrapolate")

        plt.figure(figsize=(10, 6))
        plt.axhline(0, color="gray", linestyle="--")

        for vm_id in sorted(clock_df["VM_ID"].unique()):
            if vm_id == reference_vm_id:
                continue
            vm_data = clock_df[clock_df["VM_ID"] == vm_id]
            if len(vm_data) < 2:
                print(f"Not enough points for VM {vm_id} to plot drift.")
                continue

            ref_values = f_ref(vm_data["Timestamp"])
            drift = vm_data["ClockValue"].values - ref_values
            color = vm_colors.get(vm_id, "gray")
            plt.plot(vm_data["Timestamp"], drift, marker="o", linestyle="-",
                     label=f"VM {vm_id} drift", color=color)

        plt.xlabel("System Timestamp")
        plt.ylabel(f"Clock Difference (VM - VM {reference_vm_id})")
        plt.title(f"Drift in Logical Clock Relative to VM {reference_vm_id}")
        plt.legend()

        save_path = os.path.join(out_dir, "02_clock_drift_relative_to_vm.png")
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

    # ----------- 3) Message Queue Length Over Time -----------
    queue_df = df.dropna(subset=["QueueLength"])
    if not queue_df.empty:
        plt.figure(figsize=(10, 6))
        for vm_id, group in queue_df.groupby("VM_ID"):
            color = vm_colors.get(vm_id, "gray")
            plt.plot(group["Timestamp"], group["QueueLength"], marker="o", linestyle="-",
                     label=f"VM {vm_id}", color=color)

        plt.xlabel("System Timestamp")
        plt.ylabel("Message Queue Length")
        plt.title("Message Queue Length Over Time")
        plt.legend()

        save_path = os.path.join(out_dir, "03_message_queue_length.png")
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        print("No queue length data found to plot.")

    # ----------- 4) Event Type Distribution by VM -----------
    counts = df.groupby(["VM_ID", "EventType"]).size().unstack(fill_value=0)
    event_types = ["Internal", "Sent", "Received", "Other"]
    event_types = [et for et in event_types if et in counts.columns]
    counts = counts.reindex(sorted(counts.index))

    hatch_patterns = {
        "Internal": "/",
        "Sent": "\\",
        "Received": "x",
        "Other": "."
    }

    plt.figure(figsize=(10, 6))
    bar_width = 0.15
    x_positions = np.arange(len(counts.index))

    for i, et in enumerate(event_types):
        offsets = x_positions + i * bar_width
        values = counts[et].values
        for j, vm_id in enumerate(counts.index):
            color = vm_colors.get(vm_id, "gray")
            plt.bar(offsets[j], values[j], width=bar_width,
                    color=color, hatch=hatch_patterns.get(et, ""),
                    edgecolor="black")

    total_width = len(event_types) * bar_width
    plt.xticks(x_positions + total_width / 2 - bar_width/2,
               [f"VM {vm_id}" for vm_id in counts.index])
    plt.xlabel("VM ID")
    plt.ylabel("Number of Events")
    plt.title("Event Type Distribution by VM")

    legend_patches = []
    for et in event_types:
        patch = Patch(facecolor="white", hatch=hatch_patterns.get(et, ""),
                      edgecolor="black", label=et)
        legend_patches.append(patch)
    plt.legend(handles=legend_patches, title="Event Type")

    save_path = os.path.join(out_dir, "04_event_type_distribution.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Plots saved in: {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_logs.py <log_csv_file>")
        sys.exit(1)

    csv_file = sys.argv[1]
    reference_vm = 1
    analyze_logs(csv_file, reference_vm_id=reference_vm)
