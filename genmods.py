import os
import json

def find_folders_with_at_symbol(mods_dir, output_mods_txt_file_dir, ignore_txt_file_dir, priority_mods):
    folders_with_at = []
    ignored_folders = []
    if os.path.exists(ignore_txt_file_dir):
        with open(ignore_txt_file_dir, 'r') as f:
            ignored_folders = [line.strip() for line in f.readlines()]
    for _, dirs, _ in os.walk(mods_dir):
        for dir_name in dirs:
            if dir_name.startswith('@') and dir_name not in ignored_folders:
                folders_with_at.append(dir_name)
    folders_with_at = [mod for mod in folders_with_at if mod not in priority_mods]
    sorted_mods = priority_mods + folders_with_at
    with open(output_mods_txt_file_dir, 'w') as f:
        for folder in sorted_mods:
            f.write(folder + '\n')
    print(f"Found {len(folders_with_at)} folders starting with '@' (excluding ignored ones).")

if __name__ == '__main__':
    config_file = 'Utils/config.json'
    with open(config_file, 'r') as f:
        config = json.load(f)
    mods_dir = config['mods_dir']
    output_mods_txt_file_dir = os.path.join(mods_dir, config['output_mods_txt_file_dir'])
    ignore_txt_file_dir = os.path.join(mods_dir, config['ignore_txt_file_dir'])
    priority_mods = config['priority_mods']
    find_folders_with_at_symbol(mods_dir, output_mods_txt_file_dir, ignore_txt_file_dir, priority_mods)
