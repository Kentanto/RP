import requests
import os
import sys
import subprocess

GITHUB_REPO = "Kentanto/RP"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LOCAL_VERSION_FILE = "version.txt"
DOWNLOAD_FOLDER = "dist/updates"
GAME_PATH = "minigame.exe"

def get_local_version():
    if os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, "r") as f:
            return f.read().strip()
    return "0.0.0"

def get_latest_version():
    try:
        response = requests.get(LATEST_RELEASE_URL)
        response.raise_for_status()
        latest_version = response.json()["tag_name"]
        return latest_version
    except Exception as e:
        print(f"Failed to fetch latest version: {e}")
        return None

def download_file(download_url, save_path):
    response = requests.get(download_url, stream=True)
    response.raise_for_status()
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    with open(save_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

def update_game():
    latest_version = get_latest_version()
    local_version = get_local_version()
    
    if not latest_version or latest_version == local_version:
        print("No updates available.")
    else:
        print(f"New version found: {latest_version} (Current: {local_version})")
        
        # Get the release information
        response = requests.get(LATEST_RELEASE_URL)
        response.raise_for_status()
        assets = response.json().get("assets", [])
        
        if not assets:
            print("No assets found in the latest release.")
            return
        
        # Download all assets
        for asset in assets:
            asset_name = asset["name"]
            download_url = asset["browser_download_url"]
            
            # Define save path based on the file name
            if "minigame.exe" in asset_name:
                save_path = os.path.join(DOWNLOAD_FOLDER, "minigame.exe")
            elif "icon" in asset_name:
                save_path = os.path.join(DOWNLOAD_FOLDER, "icons", asset_name)
            elif "db" in asset_name or "database" in asset_name:
                save_path = os.path.join(DOWNLOAD_FOLDER, "database", asset_name)
            else:
                save_path = os.path.join(DOWNLOAD_FOLDER, asset_name)
            
            print(f"Downloading {asset_name}...")
            download_file(download_url, save_path)
        
        # Replace the old game executable with the new one
        os.replace(os.path.join(DOWNLOAD_FOLDER, "minigame.exe"), GAME_PATH)
        
        # Update the version file
        with open(LOCAL_VERSION_FILE, "w") as f:
            f.write(latest_version)
    
    print("Update check complete. Launching game...")

    # Make sure the game exists before launching
    if os.path.exists(GAME_PATH):
        subprocess.Popen([GAME_PATH], cwd="dist")
    else:
        print("Error: minigame.exe not found!")

    sys.exit()

if __name__ == "__main__":
    update_game()
