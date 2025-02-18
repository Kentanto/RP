import requests
import os
import sys
import subprocess
import glob

GITHUB_REPO = "Kentanto/RP"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LOCAL_VERSION_FILE = "version.txt"
DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads", "Game")
GAME_FILES_FOLDER = os.path.join(DOWNLOAD_FOLDER, "files")
GAME_BASE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "minigame.py")



def get_local_version():
    """Get the version from the local version file."""
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
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    with open(save_path, "wb") as file:
        print(f"Downloads will be saved to: {os.path.abspath(save_path)}")
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

def find_game_executable():
    """Search for the folder matching minigame_V*.exe and return the path to minigame.exe."""
    game_folders = glob.glob(GAME_BASE_PATH)
    if game_folders:
        game_folder = game_folders[0]
        game_executable_path = os.path.join(game_folder, "minigame.py")
        if os.path.exists(game_executable_path):
            return game_executable_path
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
        
        for asset in assets:
            asset_name = asset["name"]
            download_url = asset["browser_download_url"]
            
            # Place updater.exe in the main game folder
            if "updater" in asset_name:
                save_path = os.path.join(DOWNLOAD_FOLDER, asset_name)
            # Everything else goes in the files subfolder
            else:
                save_path = os.path.join(GAME_FILES_FOLDER, asset_name)
            
            print(f"Downloading {asset_name}...")
            download_file(download_url, save_path)
        
        new_game_path = find_game_executable()
        if new_game_path:
            os.replace(os.path.join(DOWNLOAD_FOLDER, "minigame.py"), new_game_path)
        
        with open(LOCAL_VERSION_FILE, "w") as f:
            f.write(latest_version)
    
    print("Update check complete. Launching game...")

    game_executable = find_game_executable()
    if game_executable:
        subprocess.Popen([game_executable], cwd=os.path.dirname(game_executable))
    else:
        print("Error: No minigame executable found!")

    sys.exit()

if __name__ == "__main__":
    update_game()
