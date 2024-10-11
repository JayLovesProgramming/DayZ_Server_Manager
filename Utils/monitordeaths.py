import time
import re
import requests
import os
import glob
import json
import threading

RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"

def load_config():
    with open('Utils/config.json', 'r') as f:
        return json.load(f)

config = load_config()

log_dir_path = config['log_dir_path']
webhook_url = config['webhook_url']
steam_ids_json_file_path = config['steam_ids_json_file_path']
custom_log_path = config['custom_log_path']
query_url = config['query_url']
SEND_AI_WEBHOOKS = config['send_ai_webhooks']
BOT_NAMES = config['bot_names']
player_check_interval = config['player_check_interval']

monitoring = False
monitoring_thread = None

# Regex patterns
death_event_with_killer_pattern = re.compile(r'\[Killfeed\] (.*?) got killed by (.*?) with.*')
death_event_without_killer_pattern = re.compile(r'\[Killfeed\] (.*?) got killed\.')
fall_event_pattern = re.compile(r'\[Killfeed\] (.*?) fell to their death\.')
bled_out_event_pattern = re.compile(r'\[Killfeed\] (.*?) bled out\.')  # Existing pattern for bled out
beaten_event_pattern = re.compile(r'\[Killfeed\] (.*?) got beaten to a pulp by (.*?) with.*')
death_event_with_weapon_pattern = re.compile(r'\[Killfeed\] (.*?) got killed by (.*?) with (.*?)(?: from a distance of (\d+\s?[mM]))?\.')
survivor_killed_by_infected_pattern = re.compile(r'\[Killfeed\] \[(.*?)\] (.*?) got killed by an Infected\.')
mauled_by_brown_bear_pattern = re.compile(r'\[Killfeed\] (.*?) got mauled to death by a Brown Bear\.')
survivor_beaten_event_pattern = re.compile(r'\[Killfeed\] (.*?) got beaten to a pulp by AI (.*?) with.*')
ai_survivor_beaten_event_pattern = re.compile(r'\[Killfeed\] AI (.*?) got beaten to a pulp by AI (.*?) with.*')
survivor_bled_out_pattern = re.compile(r'\[Killfeed\] (.*?) bled out\.')
chemical_poisoning_pattern = re.compile(r'\[Killfeed\] (.*?) died from Chemical Poisoning\.')

def is_bot_player(player_name):
    """Check if the player name is in the custom bot names list or is 'AI Survivor (Raiders)'."""
    if player_name is None:
        return False
    return any(bot_name.lower() in player_name.lower() for bot_name in BOT_NAMES) or player_name == "AI Survivor (Raiders)"

def load_steam_ids():
    with open(steam_ids_json_file_path, 'r') as f:
        data = json.load(f)
    return data['steam_ids'], data['duplicateSteamIDs']

def get_latest_log_file():
    log_files = glob.glob(os.path.join(log_dir_path, "*.log"))
    if not log_files:
        return None
    return max(log_files, key=os.path.getctime)

def send_discord_webhook(content):
    data = {"content": content}
    try:
        response = requests.post(webhook_url, json=data)
        if response.status_code == 204:
            print(f"Webhook sent: {content}")
        else:
            print(f"Failed to send webhook: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending webhook: {e}")

def find_steam_id(player_name, steam_ids, duplicate_ids):
    for steam_id, info in steam_ids.items():
        if info['player_name'] == player_name:
            return steam_id
        if player_name in duplicate_ids.get(steam_id, []):
            return steam_id
    return None

def log_unreported_player(player_name):
    with open(custom_log_path, 'a') as custom_log_file:
        custom_log_file.write(f"{player_name}\n")
        print(f"Logged unreported player: {player_name}")

def clean_message(message):
    return re.sub(r'\[.*?\] ', '', message).strip()

def monitor_log_file(steam_ids, duplicate_ids):
    global monitoring
    try:
        while monitoring:
            log_file_path = get_latest_log_file()
            if log_file_path is None:
                print("No log file found. Waiting...")
                time.sleep(5)
                continue

            print(f"{GREEN}Monitoring log file: {log_file_path}{RESET}")

            try:
                with open(log_file_path, 'r') as file:
                    file.seek(0, 2)
                    while monitoring:
                        line = file.readline()
                        if not line:
                            time.sleep(1)
                            continue
                        print(f"Read line: {line.strip()}")
                        # Process the log here (omitting details for brevity)

                        message_content = None
                        player_name = None         
                        # Check for player deaths and events
                        death_match_with_weapon = death_event_with_weapon_pattern.search(line)
                        death_match_with_killer = death_event_with_killer_pattern.search(line)
                        death_match_without_killer = death_event_without_killer_pattern.search(line)
                        fall_match = fall_event_pattern.search(line)
                        survivor_beaten_match = survivor_beaten_event_pattern.search(line)
                        ai_survivor_beaten_match = ai_survivor_beaten_event_pattern.search(line)
                        bled_out_match = survivor_bled_out_pattern.search(line)  # New check for bled out
                        killed_by_infected_match = survivor_killed_by_infected_pattern.search(line)  # Check for killed by infected
                        mauled_by_brown_bear_match = mauled_by_brown_bear_pattern.search(line)  # Check for mauled by a Brown Bear
                        chemical_poisoning_match = chemical_poisoning_pattern.search(line)  # Check for chemical poison

                        # Handling survivor mauled by a Brown Bear
                        if mauled_by_brown_bear_match:
                            survivor_name = clean_message(mauled_by_brown_bear_match.group(1))
                            message_content = f"**{survivor_name}** was mauled to death by a Brown Bear!"

                        # Handling survivor killed by an Infected
                        elif killed_by_infected_match:
                            survivor_name = clean_message(killed_by_infected_match.group(1))
                            message_content = f"**{survivor_name}** got killed by an Infected!"

                        # Handling survivor bleeding out
                        elif bled_out_match:
                            survivor_name = clean_message(bled_out_match.group(1))
                            message_content = f"**{survivor_name}** has bled out!"

                        # Handling survivor beating events
                        elif survivor_beaten_match:
                            survivor_name = clean_message(survivor_beaten_match.group(1))
                            ai_name = clean_message(survivor_beaten_match.group(2))
                            message_content = f"**{survivor_name}** has been beaten to a pulp by **AI {ai_name}**!"

                        elif ai_survivor_beaten_match:
                            ai_survivor_name = clean_message(ai_survivor_beaten_match.group(1))
                            ai_killer_name = clean_message(ai_survivor_beaten_match.group(2))
                            message_content = f"**AI {ai_survivor_name}** has been beaten to a pulp by **AI {ai_killer_name}**!"

                        # Handling player deaths with weapon
                        elif death_match_with_weapon:
                            player_name = clean_message(death_match_with_weapon.group(1))
                            killer_name = clean_message(death_match_with_weapon.group(2))
                            weapon_name = clean_message(death_match_with_weapon.group(3))
                            distance = death_match_with_weapon.group(4)

                            steam_id = None
                            if not is_bot_player(player_name):
                                steam_id = find_steam_id(player_name, steam_ids, duplicate_ids)

                            if steam_id:
                                message_content = f"**{player_name}** was killed by **{killer_name}** with a **{weapon_name}**!"
                            else:
                                message_content = f"**{player_name}** was killed by **{killer_name}** with a **{weapon_name}**!"
                                log_unreported_player(player_name)

                        # Handling player deaths with killer
                        elif death_match_with_killer:
                            player_name = clean_message(death_match_with_killer.group(1))
                            killer_name = clean_message(death_match_with_killer.group(2))

                            steam_id = None
                            if not is_bot_player(player_name):
                                steam_id = find_steam_id(player_name, steam_ids, duplicate_ids)

                            if steam_id:
                                message_content = f"**{player_name}** was killed by **{killer_name}**!"
                            else:
                                message_content = f"**{player_name}** was killed by **{killer_name}**!"
                                log_unreported_player(player_name)

                        # Handling player deaths without a killer
                        elif death_match_without_killer:
                            player_name = clean_message(death_match_without_killer.group(1))
                            steam_id = None
                            if not is_bot_player(player_name):
                                steam_id = find_steam_id(player_name, steam_ids, duplicate_ids)

                            if steam_id:
                                message_content = f"**{player_name}** died!"
                            else:
                                message_content = f"**{player_name}** died!"
                                log_unreported_player(player_name)

                        # Handling fall deaths
                        elif fall_match:
                            player_name = clean_message(fall_match.group(1))
                            steam_id = None
                            if not is_bot_player(player_name):
                                steam_id = find_steam_id(player_name, steam_ids, duplicate_ids)

                            if steam_id:
                                message_content = f"**{player_name}** fell to their death!"
                            else:
                                message_content = f"**{player_name}** fell to their death!"
                                log_unreported_player(player_name)

                        # Handling deaths from chemical poisoning
                        elif chemical_poisoning_match:
                            player_name = clean_message(chemical_poisoning_match.group(1))
                            steam_id = None
                            if not is_bot_player(player_name):
                                steam_id = find_steam_id(player_name, steam_ids, duplicate_ids)

                            if steam_id:
                                message_content = f"**{player_name}** died from Chemical Poisoning!"
                            else:
                                message_content = f"**{player_name}** died from Chemical Poisoning!"
                                log_unreported_player(player_name)

                        # If a message was constructed, send it to Discord
                        if message_content:
                            send_discord_webhook(message_content)

            except Exception as e:
                print(f"Error reading log file: {e}")
    except Exception as e:
        print(f"Error in log monitoring thread: {e}")

def check_player_count():
    global monitoring
    print(f"Discord Killfeed Script Started")
    print(f"Waiting until a player joins the server")
    try:
        while True:
            try:
                response = requests.get(query_url)
                if response.status_code == 200:
                    player_data = response.json()
                    player_count = player_data.get("result", {}).get("players", 0)
                    print(f"Player count: {player_count}")
                    if player_count > 0 and not monitoring:
                        print(f"{CYAN}Players detected, starting log monitoring...{RESET}")
                        steam_ids, duplicate_ids = load_steam_ids()
                        start_monitoring(steam_ids, duplicate_ids)
                    elif player_count == 0 and monitoring:
                        print(f"{YELLOW}No players detected, stopping log monitoring...{RESET}")
                        stop_monitoring()

                else:
                    print(f"Failed to fetch player count: {response.status_code}")
            except Exception as e:
                print(f"Error checking player count: {e}")
            time.sleep(player_check_interval)
    except Exception as e:
        print(f"Error in player count thread: {e}")

def start_monitoring(steam_ids, duplicate_ids):
    global monitoring, monitoring_thread
    monitoring = True
    monitoring_thread = threading.Thread(target=monitor_log_file, args=(steam_ids, duplicate_ids))
    monitoring_thread.start()

def stop_monitoring():
    global monitoring, monitoring_thread
    monitoring = False
    if monitoring_thread:
        monitoring_thread.join()
        monitoring_thread = None

if __name__ == "__main__":
    try:
        check_thread = threading.Thread(target=check_player_count)
        check_thread.start()
        # This ensures the main program doesn't exit immediately
        check_thread.join()
    except KeyboardInterrupt:
        print(f"{YELLOW}Exiting...{RESET}")
        stop_monitoring()
