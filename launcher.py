import requests
import os
import sys
import subprocess

GITHUB_REPO = "Kentanto/RP"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LOCAL_VERSION_FILE = "version.txt"
DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads", "Game")
GAME_FILES_FOLDER = os.path.join(DOWNLOAD_FOLDER, "files")
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
UPDATER_DIR = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
GAME_FILES_DIR = os.path.join(UPDATER_DIR, "files")
GAME_EXE_PATH = os.path.join(GAME_FILES_DIR, "minigame.exe")



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
    """Search for minigame.exe in the files directory next to updater."""
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
        
        for asset in assets:
            asset_name = asset["name"]
            download_url = asset["browser_download_url"]
            
            # Skip updating updater.exe while it's running
            if "updater" in asset_name.lower():
                print("Skipping updater.exe update while running")
                continue
                
            save_path = os.path.join(GAME_FILES_DIR, asset_name)
            print(f"Downloading {asset_name}...")
            download_file(download_url, save_path)
        
        new_game_path = find_game_executable()
        if new_game_path:
            os.replace(os.path.join(DOWNLOAD_FOLDER,"files", "minigame.exe"), new_game_path)
        
        with open(LOCAL_VERSION_FILE, "w") as f:
            f.write(latest_version)
    
    print("Update check complete. Launching game...")

    game_executable = find_game_executable()
    if game_executable:
        print(f"Launching game from: {game_executable}")
        subprocess.Popen(GAME_EXE_PATH, cwd=os.path.dirname(GAME_EXE_PATH))

    else:
        print(f"Game not found in: {os.path.dirname(GAME_EXE_PATH)}")

    sys.exit()

if __name__ == "__main__":
    update_game()
