import re
import time
import os
import json
from glob import glob
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"

LOG_DIR = r"C:\DayZServer\resources\Profiles"  # Directory containing log files
STEAM_ID_LOG_PATH = r"C:\DayZServer\resources\Utils\steam_ids.json"  # Path to your Steam ID JSON file

def get_latest_log_file():
    """Returns the latest log file from the specified directory."""
    log_files = glob(os.path.join(LOG_DIR, '*.log'))  # Adjust the file extension if necessary
    return max(log_files, key=os.path.getctime) if log_files else None

def extract_player_info(log_line):
    """Extracts the player name and Steam ID from a log line."""
    match = re.search(r'Player "(.*?)" \(steamid=(\d+)\)', log_line)
    return match.groups() if match else None

def update_steam_ids(steam_ids, duplicate_ids):
    """Updates the Steam IDs JSON file."""
    with open(STEAM_ID_LOG_PATH, 'w', encoding='utf-8') as file:
        json.dump({"steam_ids": steam_ids, "duplicateSteamIDs": {k: list(v) for k, v in duplicate_ids.items()}}, file, indent=4)

def process_all_log_files():
    """Processes all log files to extract and update Steam IDs."""
    steam_ids = {}  # To store player names and Steam IDs
    duplicate_ids = {}  # To store duplicate Steam IDs and their player names
    log_files = glob(os.path.join(LOG_DIR, '*.log'))  # Get all log files

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as file:
                for line in file:
                    player_info = extract_player_info(line)
                    if player_info:
                        player_name, steam_id = player_info
                        if steam_id in steam_ids:
                            # Store the old entry in duplicate_ids using a set to avoid duplicates
                            if steam_id not in duplicate_ids:
                                duplicate_ids[steam_id] = set()
                            duplicate_ids[steam_id].add(steam_ids[steam_id]["player_name"])  # Store the old player name
                            duplicate_ids[steam_id].add(player_name)  # Add the new player name

                            # Update with the latest entry
                            steam_ids[steam_id] = {
                                "player_name": player_name,
                                "comment": "This player has a suffix" if "(2)" in player_name or "(3)" in player_name else ""
                            }
                        else:
                            steam_ids[steam_id] = {
                                "player_name": player_name,
                                "comment": "This player has a suffix" if "(2)" in player_name or "(3)" in player_name else ""
                            }
        except Exception as e:
            print(f"Error reading {log_file}: {e}")

    update_steam_ids(steam_ids, duplicate_ids)  # Update the JSON file with all found Steam IDs

def monitor_log_file(log_file_path):
    """Monitors the specified log file for new entries and updates Steam IDs."""
    steam_ids = {}  # To store player names and Steam IDs
    duplicate_ids = {}  # To store duplicate Steam IDs and their player names

    try:
        with open(log_file_path, 'r', encoding='utf-8', errors='replace') as file:
            # Move to the end of the file
            file.seek(0, 2)

            while True:
                line = file.readline()
                if not line:  # If no new line, wait a moment
                    time.sleep(0.5)
                    continue

                player_info = extract_player_info(line)
                if player_info:
                    player_name, steam_id = player_info
                    if steam_id in steam_ids:
                        # Store the old entry in duplicate_ids using a set to avoid duplicates
                        if steam_id not in duplicate_ids:
                            duplicate_ids[steam_id] = set()
                        duplicate_ids[steam_id].add(steam_ids[steam_id]["player_name"])  # Store the old player name
                        duplicate_ids[steam_id].add(player_name)  # Add the new player name

                        # Update with the latest entry
                        steam_ids[steam_id] = {
                            "player_name": player_name,
                            "comment": "This player has a suffix" if "(2)" in player_name or "(3)" in player_name else ""
                        }
                    else:
                        steam_ids[steam_id] = {
                            "player_name": player_name,
                            "comment": "This player has a suffix" if "(2)" in player_name or "(3)" in player_name else ""
                        }
                    
                    update_steam_ids(steam_ids, duplicate_ids)  # Update the JSON file with current state
                    print(f"Updated Steam ID: {player_name} -> {steam_id}")

    except Exception as e:
        print(f"Error monitoring {log_file_path}: {e}")

if __name__ == "__main__":
    # Process all existing log files at startup
    process_all_log_files()

    latest_log_file = get_latest_log_file()
    if latest_log_file:
        print(f"{CYAN}Log Steam IDs Script Started{RESET}")
        print(f"Monitoring log file: {latest_log_file}")
        monitor_log_file(latest_log_file)
    else:
        print("No log files found.")
