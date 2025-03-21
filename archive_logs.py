import os
import glob
import csv
import time

def parse_log_file(log_file_path):
    """
    Parse a single log file into a list of rows.
    Each row is [Timestamp, Event, VM_ID].
    """
    rows = []
    # Extract VM ID from filename, e.g., "vm_1.log" -> "1"
    vm_id = os.path.basename(log_file_path).split("_")[1].split(".")[0]
    with open(log_file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    log_timestamp, event_desc = line.split(" - ", 1)
                except ValueError:
                    continue  # Skip any malformed lines.
                rows.append([log_timestamp, event_desc, vm_id])
    return rows

def clear_logs(log_dir="logs"):
    """Delete all .log files in the given log directory."""
    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    for log_file in log_files:
        os.remove(log_file)
    print("Logs cleared.")

def archive_logs(log_dir="logs", archive_dir="archives", archive_filename_prefix="logs_archive"):
    """Archive all .log files from log_dir into a CSV file stored in archive_dir."""
    # Ensure the archive directory exists.
    os.makedirs(archive_dir, exist_ok=True)

    # Get all log files in the logs directory.
    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    if not log_files:
        print("No logs to archive.")
        return

    # Create a unique archive filename using a timestamp.
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    archive_filename = f"{archive_filename_prefix}_{timestamp}.csv"
    archive_filepath = os.path.join(archive_dir, archive_filename)
    
    rows = []
    # Process each log file.
    for log_file in log_files:
        # Extract VM ID from filename, e.g., "vm_1.log" -> "1"
        vm_id = os.path.basename(log_file).split("_")[1].split(".")[0]
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        # Assuming log format: "timestamp - event description"
                        log_timestamp, event_desc = line.split(" - ", 1)
                    except ValueError:
                        continue  # Skip any malformed lines.
                    rows.append([log_timestamp, event_desc, vm_id])
    
    # Write the rows to the CSV file.
    with open(archive_filepath, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Timestamp", "Event", "VM_ID"])
        writer.writerows(rows)
    print(f"Archived logs to {archive_filepath}")

def archive_and_clear_logs(log_dir="logs", archive_dir="archives", archive_filename_prefix="logs_archive"):
    """Archive logs and then clear the log directory."""
    archive_logs(log_dir, archive_dir, archive_filename_prefix)
    clear_logs(log_dir)

# For testing purposes:
if __name__ == "__main__":
    archive_and_clear_logs()
