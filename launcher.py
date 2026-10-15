"""Athas launcher — bootstrap, update, and run the game from source.

How it works:
  * Drop launcher.py anywhere and run it. If it is alone (no game/
    package next to it), it creates an "Athas" folder and clones the
    project into it — the clone already contains this launcher, so the
    standalone copy removes itself afterwards.
  * Rerun it inside that folder and it: pulls the latest changes with
    git, restores any missing tracked files, makes sure the Python
    environment (.venv + pygame) is ready, and starts the game straight
    from the .py files — no giant exe download anymore.

Needs: Python 3.9+ and git (a zip-download fallback exists when git is
missing). Everything else installs itself into .venv.

Flags:
    --no-run      update + environment only, don't start the game
    --no-update   skip the git update check
Environment:
    ATHAS_REPO_URL   override the repository to clone from
"""
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

DEFAULT_REPO_URL = "https://github.com/Kentanto/RP.git"
FOLDER_NAME = "Athas"
GAME_ENTRY = "athas.py"
VENV_DIR = ".venv"


def say(message):
    print(f"[launcher] {message}", flush=True)


def _try_popup(message):
    """Fatal errors deserve a window when a display is available."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Athas launcher", message)
        root.destroy()
    except Exception:
        pass  # no display / no tkinter — the console message is enough


def fatal(message):
    print(f"[launcher] ERROR: {message}", file=sys.stderr, flush=True)
    _try_popup(f"Athas launcher could not continue:\n\n{message}")
    sys.exit(1)


def _run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def git_available():
    return shutil.which("git") is not None


def is_project(path):
    """A folder is the game project when it has the game package + entry."""
    return (os.path.isfile(os.path.join(path, "game", "__init__.py"))
            and os.path.isfile(os.path.join(path, GAME_ENTRY)))


def venv_python(project_dir):
    if os.name == "nt":
        return os.path.join(project_dir, VENV_DIR, "Scripts", "python.exe")
    return os.path.join(project_dir, VENV_DIR, "bin", "python")


def zip_url_for(repo_url):
    """https://github.com/OWNER/REPO.git -> codeload zip of main."""
    url = repo_url[:-4] if repo_url.endswith(".git") else repo_url
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2 and parts[-2]:
        owner, repo = parts[-2], parts[-1]
        return f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/main"
    return None


def download_zip(target, zip_url):
    """Fallback for machines without git: fetch the branch zip."""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = os.path.join(tmp, "repo.zip")
            say(f"Downloading {zip_url} ...")
            urllib.request.urlretrieve(zip_url, zip_path)
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(tmp)
            top = [e for e in os.listdir(tmp)
                   if os.path.isdir(os.path.join(tmp, e)) and e != "repo.zip"]
            if len(top) != 1:
                return False
            source = os.path.join(tmp, top[0])
            os.makedirs(target, exist_ok=True)
            for item in os.listdir(source):
                shutil.move(os.path.join(source, item), os.path.join(target, item))
        return True
    except Exception as error:
        say(f"Download failed: {error}")
        return False


def bootstrap(script_path, script_dir, repo_url):
    """Alone: create the folder, clone the project, place ourselves there."""
    target = os.path.join(script_dir, FOLDER_NAME)
    say(f"Launcher is alone. Creating project folder: {target}")

    if os.path.exists(target) and not is_project(target):
        if os.path.isdir(os.path.join(target, ".git")):
            fatal(f'"{target}" looks like a broken clone. Remove it and rerun.')
        fatal(f'"{target}" already exists but is not an Athas project.')

    if not os.path.isdir(target):
        if git_available():
            say("Cloning project with git...")
            result = _run(["git", "clone", repo_url, target])
            if result.returncode != 0:
                say(f"git clone failed: {result.stderr.strip()}")
        else:
            say("git not found.")

    if not is_project(target):
        zip_url = zip_url_for(repo_url)
        if zip_url:
            say("Falling back to a zip download (get git for updates!)...")
            download_zip(target, zip_url)

    if not is_project(target):
        fatal("Could not create the project folder. Check the network and git.")

    # The clone already contains launcher.py — drop the standalone copy.
    if os.path.isfile(os.path.join(target, "launcher.py")):
        try:
            os.remove(script_path)
            say("Placed inside the project (standalone copy removed).")
        except OSError:
            say("Could not remove the standalone copy — delete it manually.")
    else:
        try:
            os.replace(script_path, os.path.join(target, "launcher.py"))
            say("Moved into the project folder.")
        except OSError:
            pass
    return target


def update_project(project_dir):
    """git pull + restore missing tracked files. Never destroys local work."""
    if not os.path.isdir(os.path.join(project_dir, ".git")):
        say("Not a git folder — skipping update check.")
        return
    if not git_available():
        say("git not found — skipping update check.")
        return

    say("Updating (git pull)...")
    result = _run(["git", "-C", project_dir, "pull", "--ff-only"])
    if result.returncode == 0:
        say("Up to date.")
    else:
        detail = (result.stderr.strip() or result.stdout.strip())
        say(f"Could not update (offline or local changes) — continuing. {detail}")

    deleted = _run(["git", "-C", project_dir, "ls-files", "--deleted"])
    missing = [line.strip() for line in deleted.stdout.splitlines() if line.strip()]
    if missing:
        for i in range(0, len(missing), 50):
            batch = missing[i:i + 50]
            restore = _run(["git", "-C", project_dir, "checkout", "--", *batch])
            if restore.returncode == 0:
                say(f"Restored {len(batch)} missing file(s).")
            else:
                say("Could not restore some missing files.")


def _ensure_pygame(python_exe, project_dir):
    probe = subprocess.run([python_exe, "-c", "import pygame"],
                           capture_output=True)
    if probe.returncode == 0:
        return True
    say("Installing dependencies (pygame)...")
    requirements = os.path.join(project_dir, "requirements.txt")
    cmd = [python_exe, "-m", "pip", "install"]
    cmd += ["-r", requirements] if os.path.isfile(requirements) else ["pygame-ce"]
    install = subprocess.run(cmd, capture_output=True, text=True)
    probe = subprocess.run([python_exe, "-c", "import pygame"],
                           capture_output=True)
    if probe.returncode != 0:
        lines = (install.stdout or install.stderr or "").strip().splitlines()
        if lines:
            say(f"pip: {lines[-1]}")
    return probe.returncode == 0


def ensure_environment(project_dir):
    """Return a python executable that can run the game."""
    vpy = venv_python(project_dir)
    if not os.path.isfile(vpy):
        say("Creating Python environment (.venv)...")
        _run([sys.executable, "-m", "venv", VENV_DIR], cwd=project_dir)
    if os.path.isfile(vpy) and _ensure_pygame(vpy, project_dir):
        say("Python environment ready.")
        return vpy
    say("Falling back to the current Python interpreter...")
    if _ensure_pygame(sys.executable, project_dir):
        return sys.executable
    fatal("Could not prepare a Python environment with pygame.\n"
          "Install it manually:  python -m pip install pygame-ce")


def run_game(project_dir, python_exe):
    say("Starting Athas...")
    code = subprocess.call([python_exe, GAME_ENTRY], cwd=project_dir)
    say(f"Game exited with code {code}.")


def main():
    args = sys.argv[1:]
    no_run = "--no-run" in args
    no_update = "--no-update" in args
    repo_url = os.environ.get("ATHAS_REPO_URL", DEFAULT_REPO_URL)

    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)

    if is_project(script_dir):
        project_dir = script_dir
        say(f"Project found here: {project_dir}")
    else:
        existing = os.path.join(script_dir, FOLDER_NAME)
        if is_project(existing):
            project_dir = existing
            say(f"Project folder found: {project_dir}")
        else:
            project_dir = bootstrap(script_path, script_dir, repo_url)

    if not no_update:
        update_project(project_dir)

    python_exe = ensure_environment(project_dir)

    if no_run:
        say("Update-only run — done.")
        return
    run_game(project_dir, python_exe)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
