#!/usr/bin/env python3
import re
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from matplotlib.patches import Patch

def make_unique_timestamps(timestamps, epsilon=1e-6):
    """
    Ensure that the array of timestamps is strictly increasing.
    If a timestamp is not greater than the previous one,
    add a small epsilon to force uniqueness.
    """
    unique_ts = []
    prev = -np.inf
    for ts in timestamps:
        if ts <= prev:
            ts = prev + epsilon
        unique_ts.append(ts)
        prev = ts
    return np.array(unique_ts)

def analyze_logs(csv_file, reference_vm_id=1):
    """
    Reads a CSV log file (assumed to have columns: Timestamp,Event,VM_ID),
    parses logical clock data, and generates:
      1) Logical Clock Evolution Over Time
      2) Clock Drift (relative to a reference VM)
      3) Message Queue Length Over Time
      4) Event Type Distribution by VM

    It also extracts parameter information from lines that start with "PARAMETERS:".
    The graphs are saved as PNGs in a subfolder under outputs/ named 'Graphs of <CSV filename>'.
    """
    # If csv_file is not an absolute path, assume it is in the archives folder.
    if not os.path.isabs(csv_file):
        csv_file = os.path.join("archives", csv_file)
    
    # Create Output Directory
    base_name = os.path.basename(csv_file)
    file_stem = os.path.splitext(base_name)[0]
    out_dir = os.path.join("outputs", f"Graphs of {file_stem}")
    os.makedirs(out_dir, exist_ok=True)
    
    # Load the CSV file (assumes header: Timestamp,Event,VM_ID)
    df = pd.read_csv(csv_file)

    # -----------------------------------------------------------
    # SHIFT TIMESTAMPS SO THE EARLIEST ONE IS AT 0
    # -----------------------------------------------------------
    if not df["Timestamp"].empty:
        min_time = df["Timestamp"].min()
        df["Timestamp"] = df["Timestamp"] - min_time

    # --- Robust extraction functions ---
    def extract_clock(event):
        """
        Extracts the clock value from an event string.
        Supports several formats and allows for optional decimals.
        Now also supports the format: 'old clock was ... now X'
        """
        patterns = [
            r"now (\d+(?:\.\d+)?)",  # new pattern for lines like "old clock was X, now Y."
            r"CLOCK_UPDATE:\s*(\d+(?:\.\d+)?)",
            r"ticked to (\d+(?:\.\d+)?)",
            r"updated clock to (\d+(?:\.\d+)?)",
            r"clock is (\d+(?:\.\d+)?)",
            r"is now (\d+(?:\.\d+)?)",
        ]
        for pat in patterns:
            match = re.search(pat, event)
            if match:
                return float(match.group(1))
        return None

    def extract_queue_length(event):
        """Attempt to extract the queue length from the event string."""
        match = re.search(r"QUEUE:\s*(\d+)", event)
        if match:
            return int(match.group(1))
        match = re.search(r"Queue length: (\d+)", event)
        if match:
            return int(match.group(1))
        return None

    def extract_parameters(event):
        """Extract parameter info from a PARAMETERS: line."""
        match = re.search(r"PARAMETERS:\s*(.*)", event)
        if match:
            return match.group(1).strip()
        return None

    # Extract parameter info
    param_df = df[df["Event"].str.contains("PARAMETERS:")]
    vm_params = {}
    for idx, row in param_df.iterrows():
        params = extract_parameters(row["Event"])
        if params:
            vm_params[int(row["VM_ID"])] = params
    
    # Extract clock values and queue lengths
    df["ClockValue"] = df["Event"].apply(extract_clock)
    df["QueueLength"] = df["Event"].apply(extract_queue_length)
    
    # Categorize events
    def categorize_event(event_str):
        if "Internal event" in event_str or "EVENT: INTERNAL" in event_str:
            return "Internal"
        elif "Sent message" in event_str or "EVENT: SENT" in event_str:
            return "Sent"
        elif "Received message" in event_str or "EVENT: RECEIVED" in event_str:
            return "Received"
        elif "SENT_DIRECT" in event_str:
            return "SentDirect"
        else:
            return "Other"
    
    df["EventType"] = df["Event"].apply(categorize_event)
    
    # Only keep rows with ClockValue for clock analysis
    clock_df = df.dropna(subset=["ClockValue"]).copy()
    # Refine duplicate removal by adding a RoundedTimestamp column (round to 5 decimals)
    clock_df["RoundedTimestamp"] = clock_df["Timestamp"].round(5)
    
    # Define a color map
    vm_colors = {1: "tab:blue", 2: "tab:orange", 3: "tab:green", 4: "tab:red", 5: "tab:purple"}
    
    # 1) Logical Clock Evolution Over Time
    plt.figure(figsize=(10, 6))
    for vm_id, group in clock_df.groupby("VM_ID"):
        color = vm_colors.get(vm_id, "gray")
        params = vm_params.get(vm_id, "")
        label = f"VM {vm_id} ({params})" if params else f"VM {vm_id}"
        plt.plot(
            group["Timestamp"],
            group["ClockValue"],
            linestyle="-",
            linewidth=0.8,
            marker=None,
            label=label,
            color=color
        )
    plt.xlabel("System Timestamp (seconds from start)")
    plt.ylabel("Logical Clock Value")
    plt.title("Logical Clock Evolution Over Time")
    plt.legend()
    plt.savefig(os.path.join(out_dir, "01_logical_clock_evolution.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2) Clock Drift Relative to a Reference VM
    ref_data = clock_df[clock_df["VM_ID"] == reference_vm_id].drop_duplicates(subset=["RoundedTimestamp"])
    if len(ref_data) < 2:
        print(f"Not enough data for reference VM {reference_vm_id} to perform interpolation. Plotting raw points instead.")
        ref_val = ref_data["ClockValue"].iloc[0] if len(ref_data) > 0 else 0
        plt.figure(figsize=(10, 6))
        plt.axhline(0, color="gray", linestyle="--")
        for vm_id in sorted(clock_df["VM_ID"].unique()):
            if vm_id == reference_vm_id:
                continue
            vm_data = clock_df[clock_df["VM_ID"] == vm_id]
            drift = vm_data["ClockValue"].values - ref_val
            color = vm_colors.get(vm_id, "gray")
            params = vm_params.get(vm_id, "")
            label = f"VM {vm_id} drift ({params})" if params else f"VM {vm_id} drift"
            plt.plot(vm_data["Timestamp"], drift, marker="o", linestyle="-", label=label, color=color)
        plt.xlabel("System Timestamp (seconds from start)")
        plt.ylabel(f"Clock Difference (VM - VM {reference_vm_id})")
        plt.title(f"Drift in Logical Clock Relative to VM {reference_vm_id} (Raw Data)")
        plt.legend()
        plt.savefig(os.path.join(out_dir, "02_clock_drift_relative_to_vm.png"), dpi=300, bbox_inches='tight')
        plt.close()
    else:
        unique_timestamps = make_unique_timestamps(ref_data["Timestamp"].values)
        f_ref = interp1d(unique_timestamps, ref_data["ClockValue"].values,
                         bounds_error=False, fill_value="extrapolate")
        plt.figure(figsize=(10, 6))
        plt.axhline(0, color="gray", linestyle="--")
        for vm_id in sorted(clock_df["VM_ID"].unique()):
            if vm_id == reference_vm_id:
                continue
            vm_data = clock_df[clock_df["VM_ID"] == vm_id]
            if len(vm_data) < 1:
                print(f"Not enough points for VM {vm_id} to plot drift.")
                continue
            ref_values = f_ref(make_unique_timestamps(vm_data["Timestamp"].values))
            drift = vm_data["ClockValue"].values - ref_values
            color = vm_colors.get(vm_id, "gray")
            params = vm_params.get(vm_id, "")
            label = f"VM {vm_id} drift ({params})" if params else f"VM {vm_id} drift"
            plt.plot(vm_data["Timestamp"], drift, marker="o", linestyle="-", label=label, color=color)
        plt.xlabel("System Timestamp (seconds from start)")
        plt.ylabel(f"Clock Difference (VM - VM {reference_vm_id})")
        plt.title(f"Drift in Logical Clock Relative to VM {reference_vm_id}")
        plt.legend()
        plt.savefig(os.path.join(out_dir, "02_clock_drift_relative_to_vm.png"), dpi=300, bbox_inches='tight')
        plt.close()
    
    # 3) Message Queue Length Over Time
    queue_df = df.dropna(subset=["QueueLength"])
    if not queue_df.empty:
        plt.figure(figsize=(10, 6))
        for vm_id, group in queue_df.groupby("VM_ID"):
            color = vm_colors.get(vm_id, "gray")
            params = vm_params.get(vm_id, "")
            label = f"VM {vm_id} ({params})" if params else f"VM {vm_id}"
            plt.plot(group["Timestamp"], group["QueueLength"], marker="o", linestyle="-", label=label, color=color)
        plt.xlabel("System Timestamp (seconds from start)")
        plt.ylabel("Message Queue Length")
        plt.title("Message Queue Length Over Time")
        plt.legend()
        plt.savefig(os.path.join(out_dir, "03_message_queue_length.png"), dpi=300, bbox_inches='tight')
        plt.close()
    else:
        print("No queue length data found to plot.")
    
    # 4) Event Type Distribution by VM
    counts = df.groupby(["VM_ID", "EventType"]).size().unstack(fill_value=0)
    event_types = ["Internal", "Sent", "Received", "SentDirect", "Other"]
    event_types = [et for et in event_types if et in counts.columns]
    counts = counts.reindex(sorted(counts.index))
    hatch_patterns = {"Internal": "/", "Sent": "\\", "Received": "x", "SentDirect": "o", "Other": "."}

    # Increase figure size to accommodate rotated x-tick labels
    plt.figure(figsize=(12, 6))

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

    # Update x-tick labels to include parameter info and rotate them
    xtick_labels = [f"VM {vm_id} ({vm_params.get(vm_id, '')})" for vm_id in sorted(counts.index)]
    plt.xticks(
        x_positions + total_width / 2 - bar_width/2,
        xtick_labels,
        rotation=15,   # Rotate by 15 degrees
        ha="right"     # Align labels to the right
    )

    plt.xlabel("VM ID")
    plt.ylabel("Number of Events")
    plt.title("Event Type Distribution by VM")

    legend_patches = []
    for et in event_types:
        patch = Patch(facecolor="white", hatch=hatch_patterns.get(et, ""),
                      edgecolor="black", label=et)
        legend_patches.append(patch)
    plt.legend(handles=legend_patches, title="Event Type")
    plt.savefig(os.path.join(out_dir, "04_event_type_distribution.png"),
                dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Plots saved in: {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_logs.py <log_csv_file>")
        sys.exit(1)
    csv_file = sys.argv[1]
    reference_vm = 1
    analyze_logs(csv_file, reference_vm_id=reference_vm)
