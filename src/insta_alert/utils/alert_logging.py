import os
from colorama import Fore, Back

def load_posted_alerts(log_file_path):
    """
    Loads already posted alert IDs from the log file into a set.
    This prevents reposting alerts if the script is restarted.
    Args:
        file (.log file): file with a list of posted alert IDs
    Returns:
        (set): set of posted alert IDs
    """
    # Ensure the directory for the log file exists.
    log_dir = os.path.dirname(log_file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Create the log file if it doesn't exist.
    if not os.path.exists(log_file_path):
        with open(log_file_path, 'w') as f:
            pass # Create an empty file
        print(Fore.YELLOW + f"Log file not found. Created a new one at: {log_file_path}" + Fore.RESET)
        return set()

    # Read the alert IDs from the file.
    try:
        with open(log_file_path, 'r') as f:
            posted_alerts = {line.strip() for line in f if line.strip()}
            print(Back.GREEN + Fore.BLACK + f"Successfully loaded {len(posted_alerts)} posted alerts from {log_file_path}" + Back.RESET)
            return posted_alerts
    except Exception as e:
        print(Back.RED + f"Error loading log file {log_file_path}: {e}. Returning empty set." + Back.RESET)
        return set()
    
def save_posted_alert(alert_id, log_file_path):
    """
    Appends a new alert ID to the log file for persistence.
    Args:
        id (alert_id): ID object from the *properties* part of the alert, starting with urn:oid:
        file (.log file): The log file to be saving things to. 
    Returns:
        bool: if it was successful or not
    """
    try:
        # Open the file in append mode ('a') and add the new ID
        with open(log_file_path, 'a') as f:
            f.write(f"{alert_id}\n")
            return True
    except Exception as e:
        print(Fore.RED + f"Error saving alert ID to log: {e}" + Fore.RESET)
        return False