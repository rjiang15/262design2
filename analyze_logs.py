import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

def parse_log_file(file_path):
    """Parse a VM log file into a DataFrame."""
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            # Each log line is in the format:
            # TIMESTAMP - Event description
            parts = line.strip().split(" - ", 1)
            if len(parts) == 2:
                try:
                    timestamp = float(parts[0])
                except ValueError:
                    continue
                event = parts[1]
                data.append({"timestamp": timestamp, "event": event})
    return pd.DataFrame(data)

def load_all_logs(log_dir="logs"):
    """Load and combine logs from all VMs."""
    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    all_dfs = []
    for log_file in log_files:
        df = parse_log_file(log_file)
        # Add a column for the VM ID extracted from the filename (e.g., vm_1.log)
        vm_id = os.path.basename(log_file).split("_")[1].split(".")[0]
        df["vm_id"] = int(vm_id)
        all_dfs.append(df)
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_df.sort_values("timestamp", inplace=True)
        return combined_df
    return pd.DataFrame()

def plot_clock_events(df):
    """
    Plot the logical clock events extracted from the event descriptions.
    This is a simple example that extracts numbers from the event strings.
    """
    # We'll assume that events mention "clock ticked to X" or "clock is now X"
    def extract_clock(event):
        import re
        m = re.search(r"clock (ticked to|is now) (\d+)", event)
        if m:
            return int(m.group(2))
        return None
    
    df["clock"] = df["event"].apply(extract_clock)
    df = df.dropna(subset=["clock"])
    
    # Plot for each VM
    fig, ax = plt.subplots()
    for vm_id, group in df.groupby("vm_id"):
        ax.plot(group["timestamp"], group["clock"], marker="o", linestyle="-", label=f"VM {vm_id}")
    
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Logical Clock Value")
    ax.set_title("Logical Clock Evolution Over Time")
    ax.legend()
    plt.show()

if __name__ == "__main__":
    df_logs = load_all_logs()
    if df_logs.empty:
        print("No logs found in the 'logs' directory.")
    else:
        print(df_logs)
        plot_clock_events(df_logs)
        # Optionally, save the combined logs for further analysis.
        df_logs.to_csv("combined_logs.csv", index=False)
