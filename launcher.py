import requests
import os
import sys
import subprocess
import hashlib
import json
import tkinter as tk
from tkinter import messagebox

LATEST_RELEASE_URL = f"https://api.github.com/repos/Kentanto/RP/releases/latest"
LOCAL_VERSION_FILE = "version.txt"
DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads", "Athas")
GAME_FILES_FOLDER = os.path.join(DOWNLOAD_FOLDER, "files")
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
LAUNCHER_DIR = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
GAME_FILES_DIR = os.path.join(LAUNCHER_DIR, "files") if os.path.exists(os.path.join(LAUNCHER_DIR, "version.txt")) else os.path.join(DOWNLOAD_FOLDER, "files")
GAME_EXE_PATH = os.path.join(GAME_FILES_DIR, "athas.exe")



def get_local_version():
    """Get the version from the local version file."""
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    if os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, "r") as f:
            return f.read().strip()
    return "0.0.0"


def download_file(download_url, save_path):
    """Download a file from the given URL and save it to the specified path."""
    response = requests.get(download_url, stream=True)
    response.raise_for_status()

    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, "wb") as file:
        print(f"Downloads will be saved to: {os.path.abspath(save_path)}")
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

def show_error_popup(message):
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error launching game", message)
    root.destroy()

def find_game_executable():
    """Search for athas.exe in the files directory next to updater."""
    print(f"Looking for game at: {GAME_EXE_PATH}")
    if os.path.exists(GAME_EXE_PATH):
        return GAME_EXE_PATH
    return None

def file_matches(asset, local_path):
    if not os.path.exists(local_path):
        return False
    # Compare file size
    local_size = os.path.getsize(local_path)
    if local_size != asset["size"]:
        return False
    return True

def get_local_file_versions():
    """Read version.txt as a dict of {filename: updated_at}."""
    if os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def save_local_file_versions(file_versions):
    """Save the file version dict to version.txt."""
    with open(LOCAL_VERSION_FILE, "w") as f:
        json.dump(file_versions, f)

def update_game():
    local_file_versions = get_local_file_versions()
    response = requests.get(LATEST_RELEASE_URL)
    response.raise_for_status()
    assets = response.json().get("assets", [])
    new_file_versions = local_file_versions.copy()  # Start with existing

    os.makedirs(GAME_FILES_DIR, exist_ok=True)

    for asset in assets:
        asset_name = asset["name"]
        asset_updated = asset["updated_at"]
        download_url = asset["browser_download_url"]
        save_path = os.path.join(GAME_FILES_DIR, asset_name)

        # Download if missing or outdated
        if (asset_name not in local_file_versions or
            asset_updated > local_file_versions.get(asset_name, "")):
            print(f"Downloading {asset_name}...")
            download_file(download_url, save_path)
            new_file_versions[asset_name] = asset_updated
        else:
            print(f"{asset_name} is up to date, skipping download.")

    # Save updated file versions dict
    save_local_file_versions(new_file_versions)


    
    print("Update check complete. Launching game...")

    game_executable = find_game_executable()
    if game_executable:
        print(f"Launching athas system from: {game_executable}")
        try:
            subprocess.Popen(GAME_EXE_PATH, cwd=os.path.dirname(GAME_EXE_PATH))
        except Exception as e:
            show_error_popup(str(e))
    else:
        error_msg = f"Game not found in: {os.path.dirname(GAME_EXE_PATH)}"
        print(error_msg)
        show_error_popup(error_msg)


    def should_delete_self():
        
        updater_path = os.path.abspath(sys.argv[0])
        updater_dir = os.path.dirname(updater_path)
        
        files_folder = os.path.join(updater_dir, "files")
        version_txt = os.path.join(updater_dir, "version.txt")
        
        print(f"Files folder exists: {os.path.exists(files_folder)}")
        print(f"Version.txt exists: {os.path.exists(version_txt)}")

        if not os.path.exists(files_folder) and not os.path.exists(version_txt):
            return True
        return False

    def delete_self():
        if not should_delete_self():
            print("Conditions not met. \nSkipping self-deletion.")
            return

        updater_path = sys.argv[0]
        delete_script = f'''@echo off
                            timeout /t 3 /nobreak >nul
                            del "{updater_path}" /f /q
                            del "%~f0"'''
        delete_cmd = os.path.join(os.path.dirname(updater_path), "delete_updater.bat")

        with open(delete_cmd, "w") as f:
            f.write(delete_script)

        subprocess.Popen(["cmd", "/c", delete_cmd], creationflags=subprocess.CREATE_NO_WINDOW)
        print("Conditions met. \nUpdater scheduled for deletion.")

    athas_version_path = os.path.join(DOWNLOAD_FOLDER, "version.txt")
    if os.path.abspath(LOCAL_VERSION_FILE) != os.path.abspath(athas_version_path):
        try:
            os.replace(LOCAL_VERSION_FILE, athas_version_path)
            print(f"Moved version.txt to {athas_version_path}")
        except Exception as e:
            print(f"Failed to move version.txt: {e}")

    delete_self()

    sys.exit()

if __name__ == "__main__":
    import traceback
    try:
        update_game()
    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        show_error_popup(f"An unexpected error occurred:\n\n{tb}")