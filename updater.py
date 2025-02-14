import requests
import os
import sys
import subprocess

GITHUB_REPO = "yourusername/yourrepository"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LOCAL_VERSION_FILE = "version.txt"
DOWNLOAD_FOLDER = "updates"

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

def download_latest_release(download_url, save_path):
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
        return
    
    print(f"New version found: {latest_version} (Current: {local_version})")
    
    response = requests.get(LATEST_RELEASE_URL)
    assets = response.json()["assets"]
    exe_asset = next((asset for asset in assets if asset["name"].endswith(".exe")), None)
    
    if not exe_asset:
        print("No executable found in the latest release.")
        return
    
    exe_url = exe_asset["browser_download_url"]
    save_path = os.path.join(DOWNLOAD_FOLDER, "game.exe")
    
    print("Downloading update...")
    download_latest_release(exe_url, save_path)
    
    print("Replacing old game with the new version...")
    os.replace(save_path, "game.exe")
    
    with open(LOCAL_VERSION_FILE, "w") as f:
        f.write(latest_version)
    
    print("Update complete! Restarting game...")
    subprocess.Popen(["game.exe"])
    sys.exit()

if __name__ == "__main__":
    update_game()
