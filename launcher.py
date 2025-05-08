import requests
import os
import sys
import subprocess

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

def get_latest_version():
    """Get the latest version from the GitHub API."""
    try:
        response = requests.get(LATEST_RELEASE_URL)
        response.raise_for_status()
        latest_version = response.json()["tag_name"]
        return latest_version
    except Exception as e:
        print(f"Failed to fetch latest version: {e}")
        return None


def download_file(download_url, save_path):
    """Download a file from the given URL and save it to the specified path."""
    response = requests.get(download_url, stream=True)
    response.raise_for_status()
    
    if save_path.endswith('.mp3'):
        songs_dir = os.path.join(os.path.dirname(save_path), 'songs')
        os.makedirs(songs_dir, exist_ok=True)
        save_path = os.path.join(songs_dir, os.path.basename(save_path))
    else:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    with open(save_path, "wb") as file:
        print(f"Downloads will be saved to: {os.path.abspath(save_path)}")
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

def find_game_executable():
    """Search for athas.exe in the files directory next to updater."""
    print(f"Looking for game at: {GAME_EXE_PATH}")
    if os.path.exists(GAME_EXE_PATH):
        return GAME_EXE_PATH
    return None

def update_game():
    """Update the game by downloading the latest version if available."""
    latest_version = get_latest_version()
    local_version = get_local_version()
    
    if not latest_version or latest_version == local_version:
        print("No updates available.")
    else:
        print(f"New version found: {latest_version} (Current: {local_version})")
        
        response = requests.get(LATEST_RELEASE_URL)
        response.raise_for_status()
        assets = response.json().get("assets", [])
        
        if not assets:
            print("No assets found in the latest release.")
            return
        
        os.makedirs(GAME_FILES_DIR, exist_ok=True)
        
        for asset in assets:
            asset_name = asset["name"]
            download_url = asset["browser_download_url"]
            save_path = os.path.join(GAME_FILES_DIR, asset_name)
            print(f"Downloading {asset_name}...")
            download_file(download_url, save_path)
        with open(LOCAL_VERSION_FILE, "w") as f:
            f.write(latest_version)
        target_version_path = os.path.join(LAUNCHER_DIR, "Athas","version.txt")
        if not target_version_path:
            target_version_path = os.path.join(LAUNCHER_DIR, "version.txt")
        if os.path.exists(LOCAL_VERSION_FILE):
            os.replace(LOCAL_VERSION_FILE, target_version_path)
            print(f"Moved version.txt to {target_version_path}")

    
    print("Update check complete. Launching game...")

    game_executable = find_game_executable()
    if game_executable:
        print(f"Launching athas system from: {game_executable}")
        subprocess.Popen(GAME_EXE_PATH, cwd=os.path.dirname(GAME_EXE_PATH))
    else:
        print(f"Game not found in: {os.path.dirname(GAME_EXE_PATH)}")


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

    delete_self()

    sys.exit()

if __name__ == "__main__":
    update_game()
