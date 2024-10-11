import os
import subprocess
import time
import requests
import threading
import json
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import tkinter.font as tkFont
from datetime import datetime
import json
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import re

invalid_workshop_mod_id = r'{"status":1,"error":"steam workshop id not found - (\d+)"}'
monitoring_process = None
server_process = None
stop_monitor_process = False 
previously_highlighted = None

Window = ttk.Window()

# Destroys the windows and displays a message box with the error message
def show_error_message(title: str, message: str):
    Window.destroy()
    messagebox.showerror(title, message)

# Try and load the config.json
try:
    with open('Utils\\config.json', 'r') as config_file:
        config = json.load(config_file)
except FileNotFoundError:
    show_error_message("File Not Found", "Configuration file not found. Please check the file path.")
except json.JSONDecodeError:
    show_error_message("JSON Error", "Error decoding JSON. Please check the JSON format.")
except Exception as e:
    show_error_message("Unexpected Error", f"An unexpected error occurred: {e}")

# Initalize all the config.json variables
if 'config' in locals():
    server_name = config["server_name"]
    server_endpoint = config["server_endpoint"]
    server_port = config["server_port"]
    dzsa_query_port = config["dzsa_query_port"]
    prefix_directory = config["prefix_directory"]
    server_dir = config["server_dir"]
    server_config_dir = config["server_config_dir"]
    genmods_py_dir = config["genmods_py_dir"]
    mods_txt_dir = config["mods_txt_dir"]
    monitordeaths_dir = config["monitordeaths_dir"]
    steam_ids_script_dir = config["steam_ids_script_dir"]
    cpu_cores = config["cpu_cores"]
    retry_limit = config["retry_limit"]
    auto_start = config["auto_start"]
    dzsa_query_endpoint = f"http://dayzsalauncher.com/api/v1/query/{server_endpoint}/{dzsa_query_port}"
    dzsa_query_response = ""
    mod_list = []

# Initialization
def init():
    os.chdir(server_dir)
    run_genmods()
    read_mods()

# The log function for the text box so we can actually see the logs in real time
def DayZPrint(type, param):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{current_time}]: {param}\n"
    # log_entry = f"[{current_time}] [{type}]: {param}\n"
    if type == "Info":
        log_text.insert(tk.END, log_entry, "info")
    elif type == "Success":
        log_text.insert(tk.END, log_entry, "success") 
    elif type == "Warning":
        log_text.insert(tk.END, log_entry, "warning")
    elif type == "Error":
        log_text.insert(tk.END, log_entry, "error") 
    else:
        log_text.insert(tk.END, log_entry)
    log_text.see(tk.END)

# Read the mods list from mods.txt and assign it to a variable
def read_mods():
    global mod_list
    with open(mods_txt_dir, "r") as value:
        mod_list = [line.strip() for line in value if line.strip()]

# Generate the mods via genmods.py
def run_genmods():
    process = subprocess.Popen(["pythonw", genmods_py_dir], cwd=server_dir)
    process.wait()

def run_discord_killfeed():
    cmd = "start cmd /k python " + monitordeaths_dir  # Using 'start' to create a new window
    subprocess.Popen(cmd, cwd=server_dir, shell=True)

def run_log_steam_ids():
    cmd = "start cmd /k python " + steam_ids_script_dir  # Using 'start' to create a new window
    subprocess.Popen(cmd, cwd=server_dir, shell=True)

# Query response checker
def receivedInvalidQuery(response_text):
    invalid_workshop = re.search(invalid_workshop_mod_id, response_text)
    if invalid_workshop:
        workshop_id = invalid_workshop.group(1)
        DayZPrint("Error", f"There is an invalid steam workshop mod ({workshop_id}), please remove it or update it")
        return True
    if '"error":"Timeout has occurred"' in response_text:
        DayZPrint("Warning", "Retrying...")
        return True
    return False

# Query Server. Waits until the server is ready then queries DZSA launcher so that it updates to the launcher and all clients
def query_server():
    time.sleep(80)
    DayZPrint("Info", "Updating DZSA Launcher")
    max_retries = 15  # Number of retries
    retries = 0      # Initialize retry count
    while retries <= max_retries:
        try:
            response = requests.get(dzsa_query_endpoint)
            response_text = response.text
            # Check for invalid workshop mod
            if receivedInvalidQuery(response_text):
                retries += 1
                time.sleep(30)  # Wait before retrying
                continue
            DayZPrint("Info", "DZSA Launcher Update Successful")
            return response_text  # Successful response
        except requests.RequestException as value:
            DayZPrint("Error", f"Querying the server: {value}")
            return ""
    DayZPrint("Error", "Max retries reached. Server query failed.")
    return ""  # Return empty string after max retries

# Monitor Server and Restart if Terminated
def monitor_server():
    global server_process, stop_monitor_process
    while not stop_monitor_process:
        time.sleep(10)
        # Check if the server process has terminated
        if server_process and server_process.poll() is not None:  # Process has terminated (crashed or stopped)
            DayZPrint("Error", "Server process terminated - restarting server")
            # Ensure the server is completely stopped
            stop_server()
            time.sleep(10)  # Small delay before restarting
            # Restart the server process
            server_process = start_server()
            Window.after(0, DayZPrint, "Success", "Server Restarted")
            # After restarting, query the server immediately
            query_server()


# Start Server
def start_server():
    mod_string = ";".join(mod_list)
    read_mods()
    command = [
        "./DayZServer_x64",  # Assuming the server executable is named DayZServer_x64
        "-profiles=Profiles",
        "-maxMem=2048",
        f"-mod={mod_string}",
        f"-config={server_config_dir}",
        f"-port={server_port}",
        f"-cpuCount={cpu_cores}",
        "-dologs",
        "-adminlog",
        "-netlog",
        "-freezecheck"
    ]
    process = subprocess.Popen(command, cwd=server_dir)
    # threading.Thread(target=query_server, daemon=True).start()  # Run the query_server function in a separate thread
    return process

# Stop Server
def stop_server():
    global server_process
    if server_process:
        server_process.terminate()
        server_process.wait()
        server_process = None

# Start Server Button
def start_server_gui():
    global server_process, monitoring_process, stop_monitor_process
    try:
        init()
    except Exception as e:
        DayZPrint("Error", f"Initialization failed: {e}")
        messagebox.showerror("Error", f"Initialization failed: {e}")
        return
    server_process = start_server()
    DayZPrint("Success", "Server Booting Up")
    # Start querying in a separate thread
    threading.Thread(target=query_server, daemon=True).start()  # Run the query_server function in a separate thread
    # Start monitoring in a separate thread
    monitoring_process = threading.Thread(target=monitor_server, daemon=True)
    monitoring_process.start()

# Toggle auto start button
def toggle_auto_start():
    global auto_start
    auto_start = not auto_start
    if auto_start:
        should_auto_start_button.config(text="Auto Start: Enabled")
    else:
        should_auto_start_button.config(text="Auto Start: Disabled")
    try:
        # Read the existing config.json file
        with open('Utils/config.json', 'r') as file:
            config = json.load(file)
    except FileNotFoundError:
        # If the file doesn't exist, start with an empty config
        return DayZPrint("Error", "Check your config.json for any errors")
    config['auto_start'] = auto_start
    with open('Utils/config.json', 'w') as file:
        json.dump(config, file, indent=4)

# Stop Server Button
def stop_server_gui():
    global stop_monitor_process
    stop_monitor_process = True
    stop_server()
    DayZPrint("Info", "Server Stopped")
    messagebox.showinfo("Info", "Server has been stopped")

# Generate mods button
def generate_mods_gui():
    try:
        DayZPrint("Info", "Generating mods...")
        run_genmods()
        DayZPrint("Success", "Mods generated successfully.")
    except Exception as e:
        DayZPrint("Error", f"Failed to generate mods: {e}")
        messagebox.showerror("Error", f"Failed to generate mods: {e}")

# Make sure that they want to quit the application so we don't accidentally close the entire server
def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit? This will stop the server if it's running."):
        stop_server()
        Window.destroy()

# Restart server button
def restart_server():
    global server_process
    DayZPrint("Info", "Restarting server...")
    stop_server()  # Stop the server
    time.sleep(2)  # Optional delay before starting again
    server_process = start_server()  # Start the server again
    DayZPrint("Success", "Server Restarted")

def create_init_log_message(log_text):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text.insert(tk.END, f"[{current_time}]: ", "default")
    log_text.insert(tk.END, "DayZ Server Manager Initialized\n")

# Open text editor function
def open_text_editor(file_name):
    file_path = os.path.join(prefix_directory, file_name)  # Define the path to the file
    # Create a new window for the text editor
    editor_window = tk.Toplevel(Window)
    editor_window.title(f"Edit {file_name}")
    # Create a frame to hold the text area and the scrollbar
    frame = tk.Frame(editor_window)
    frame.pack(expand=True, fill='both')
    # Create a text area for editing
    text_area = tk.Text(frame, wrap='word', font=custom_font)
    text_area.pack(side=tk.LEFT, expand=True, fill='both')
    # Create a scrollbar
    scrollbar = tk.Scrollbar(frame, command=text_area.yview)
    scrollbar.pack(side=tk.RIGHT, fill='y')
    # Configure the text area to use the scrollbar
    text_area.config(yscrollcommand=scrollbar.set)
    # Load the contents of the file into the text area
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            text_area.insert(tk.END, file.read())
    # Create a save button to save changes
    def save_changes():
        with open(file_path, 'w') as file:
            file.write(text_area.get(1.0, tk.END))  # Write the text area content to the file
        messagebox.showinfo("Info", "Changes saved successfully.")
        editor_window.destroy()  # Close the editor window after saving
    save_button = tk.Button(editor_window, text="Save Changes", command=save_changes)
    save_button.pack(pady=10)
    cancel_button = tk.Button(editor_window, text="Cancel", command=editor_window.destroy)
    cancel_button.pack(pady=5)
    # Stack to keep track of deleted lines and their indices
    deleted_lines_stack = []
    # Function to delete the selected line
    def delete_selected_line(event):
        # Get the current cursor position
        current_line_index = text_area.index("insert").split('.')[0]
        # Get the content of the current line
        current_line = text_area.get(f"{current_line_index}.0", f"{current_line_index}.end")
        if current_line:  # Check if the line is not empty
            # Save the deleted line and its index for potential undo
            deleted_lines_stack.append((current_line, current_line_index))
            # Remove the line from the text area
            text_area.delete(f"{current_line_index}.0", f"{current_line_index}.end + 1 char")  # +1 char to remove the newline
    # Function to restore the last deleted line
    def restore_deleted_line():
        if deleted_lines_stack:
            # Pop the last deleted line and its index
            deleted_line, line_index = deleted_lines_stack.pop()
            # Reinsert the deleted line back into the text area
            text_area.insert(f"{line_index}.0", deleted_line + '\n')  # Add the deleted line back
    text_area.bind('<Control-x>', delete_selected_line)
    text_area.bind('<Control-z>', lambda event: restore_deleted_line())


Window.title(f"DayZ Server Manager: {server_name}")
Window.geometry("900x600")
Window.resizable(False, True)
custom_font = tkFont.Font(family="Tahoma", size=10)  # Change "Helvetica" and 12 to your desired font family and size

# All da buttons!
# Start
start_button = tk.Button(Window, text="Start Server", command=start_server_gui, width=18, height=2)
start_button.grid(row=0, column=0, padx=5, pady=5)  # Place in row 0, column 0
# Stop
stop_button = tk.Button(Window, text="Stop Server", command=stop_server_gui, width=18, height=2)
stop_button.grid(row=0, column=1, padx=5, pady=5)  # Place in row 0, column 1
# Restart
restart_button = tk.Button(Window, text="Restart Server", command=restart_server, width=18, height=2)
restart_button.grid(row=0, column=2, padx=5, pady=5)  # Place in row 0, column 2
# Generate
generate_mods_button = tk.Button(Window, text="Generate Mods", command=generate_mods_gui, width=18, height=2)
generate_mods_button.grid(row=0, column=3, padx=5, pady=5)  # Place in row 0, column 3
# Edit ignore.txt
edit_ignore_button = tk.Button(Window, text="Edit ignore.txt", command=lambda: open_text_editor("ignore.txt"), width=18, height=2)
edit_ignore_button.grid(row=0, column=4, padx=5, pady=5)  # Place in row 0, column 4
# Edit mods.txt
edit_mods_button = tk.Button(Window, text="Edit mods.txt", command=lambda: open_text_editor("mods.txt"), width=18, height=2)
edit_mods_button.grid(row=1, column=0, padx=5, pady=5)  # Place in row 0, column 4
# Edit config.json
edit_config_button = tk.Button(Window, text="Edit config.json", command=lambda: open_text_editor("config.json"), width=18, height=2)
edit_config_button.grid(row=1, column=1, padx=5, pady=5)  # Place in row 0, column 4
# Auto start
should_auto_start_button = tk.Button(Window, text="Auto Start: Enabled" if auto_start else "Auto Start: Disabled", command=toggle_auto_start, width=18, height=2)
should_auto_start_button.grid(row=1, column=2, padx=5, pady=5)
# Log text box
log_text = scrolledtext.ScrolledText(Window, width=120, height=200, state='normal', font=custom_font)
log_text.grid(row=2, column=0, columnspan=5, pady=10)  # Log text spans all columns

# Create the initial log message in the window
create_init_log_message(log_text)

# Handle closing the window
Window.protocol("WM_DELETE_WINDOW", on_closing)

# The window icon
Window.iconbitmap(r'Utils\small.ico')

# Run the discord killfeed script
run_discord_killfeed()

# Run the log steam ids script
run_log_steam_ids()

# The windows main loop (to draw it?)
Window.mainloop()











# WORK IN PROGRESS
# Text highlighting stuff
log_text.tag_configure("highlight", background="lightblue")  # Change to your desired color
def highlight_selection():
    global previously_highlighted
    try:
        start_index = log_text.index(tk.SEL_FIRST)
        end_index = log_text.index(tk.SEL_LAST)
        if previously_highlighted:
            log_text.tag_remove("highlight", previously_highlighted[0], previously_highlighted[1])
        log_text.tag_add("highlight", start_index, end_index)
        previously_highlighted = (start_index, end_index)
    except tk.TclError:
        pass

def reset_highlight():
    global previously_highlighted
    if previously_highlighted:
        log_text.tag_remove("highlight", previously_highlighted[0], previously_highlighted[1])
        previously_highlighted = None 

log_text.bind("<<Selection>>", highlight_selection)
log_text.bind("<ButtonRelease-1>", reset_highlight)