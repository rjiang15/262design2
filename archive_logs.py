import os
import glob
import csv
import time

def archive_and_clear_logs(log_dir="logs", archive_dir="archives", archive_filename_prefix="logs_archive"):
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
    # Save the CSV file in the archive directory.
    archive_filepath = os.path.join(archive_dir, archive_filename)
    
    rows = []
    # Process each log file.
    for log_file in log_files:
        vm_id = os.path.basename(log_file).split("_")[1].split(".")[0]  # e.g., vm_1.log -> 1
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
    
    # Delete old log files.
    for log_file in log_files:
        os.remove(log_file)
    print("Old log files deleted.")

# Example usage in main.py (before starting a new experiment)
if __name__ == "__main__":
    archive_and_clear_logs()  # Archive and clear old logs first.
