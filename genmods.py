import os

def find_folders_with_at_symbol(directory, output_file, ignore_file, priority_mods):
    # List to hold folder names
    folders_with_at = []
    ignored_folders = []
    # Read ignore.txt to get a list of folders to ignore
    if os.path.exists(ignore_file):
        with open(ignore_file, 'r') as f:
            ignored_folders = [line.strip() for line in f.readlines()]
    # Walk through the directory and its subdirectories
    for _, dirs, _ in os.walk(directory):
        for dir_name in dirs:
            if dir_name.startswith('@') and dir_name not in ignored_folders:
                folders_with_at.append(dir_name)
    # Remove any priority mods that were found to avoid duplicates
    folders_with_at = [mod for mod in folders_with_at if mod not in priority_mods]
    # Combine priority mods with the rest of the mods
    sorted_mods = priority_mods + folders_with_at
    # Write the folder names to the specified output text file
    with open(output_file, 'w') as f:
        for folder in sorted_mods:
            f.write(folder + '\n')
    print(f"Found {len(folders_with_at)} folders starting with '@' (excluding ignored ones).")
    # print(f"Mods with priority: {', '.join(priority_mods)}")
    # print(f"Saved to {output_file}.")

if __name__ == '__main__':
    directory = r"C:\DayZServer\resources\Utils"  # Use the current working directory
    output_file_path = os.path.join(directory, 'mods.txt')
    ignore_file_path = os.path.join(directory, 'ignore.txt')
    
    # List of priority mods (these will be listed first in the output file)
    priority_mods = ["@CF", "@Dabs Framework", "@VPPAdminTools", '@DayZ-Expansion-Bundle', "@DayZ-Expansion-Licensed", "@DayZ-Expansion-Animations", "@DayZ Editor Loader", "@HMB", "@MuchFramework", "@MuchStuffPack"]  # Example priority list
    
    find_folders_with_at_symbol(r"C:\DayZServer\resources", output_file_path, ignore_file_path, priority_mods)
