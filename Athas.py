"""
Athas Launcher — bootstraps a full game installation and starts the app.

What it does, in order:
  1. Finds the install folder (the launcher's own folder).
  2. Makes sure the game repo is there:
       - folder is already a git clone  -> uses it as-is
       - otherwise                      -> clones the repo into ./RP
       - existing clone                 -> full update (code + content)
  3. Makes sure a Python environment (.venv) exists in the repo and has
     the required libraries (PySide6 — installed from requirements.txt).
  4. Launches main.py inside that environment.

Run it:
    python launcher.py                 # normal use
    python launcher.py --check         # set everything up but don't launch
    python launcher.py --target PATH  # install into a specific folder
    python launcher.py --repo URL      # use a different repo url

Turn it into an exe (run this on the OS you want the exe for):
    pip install pyinstaller
    pyinstaller --onefile launcher.py
(Keep the console window — it shows download/install progress the first
time someone runs the game. --noconsole also works, but then the setup
steps happen invisibly.)

If Git or Python are missing (Windows), the launcher sets them up by
itself — no installer window, no admin rights:
  - Python: official installer run in silent mode, added to PATH.
  - Git: portable copy extracted into tools/PortableGit (added to PATH too).
On Linux it stops with an install hint instead.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO_URL = "https://github.com/Kentanto/RP.git"
VENV_NAME = ".venv"
INSTALL_SUBDIR = "RP"
FALLBACK_REQUIREMENTS = ["PySide6>=6.5.0"]
TOOLS_DIR = "tools"        # bootstrap downloads (git/python) land here
PY_VERSION = "3.12.10"    # pinned — last 3.12 release with a binary installer
GIT_VERSION = "2.47.1"    # pinned — Portable Git for Windows

_GIT = "git"               # resolved to a real path by ensure_git()

_MISSING = object()


def json_merge(base, ours, theirs):
    """Semantic 3-way merge for JSON data (the remote version, 'ours',
    wins whenever both sides changed the same field differently)."""
    if not (isinstance(base, dict) and isinstance(ours, dict) and isinstance(theirs, dict)):
        if ours == theirs or base == theirs:
            return ours
        if base == ours:
            return theirs
        return ours
    result = dict(ours)
    for key in set(base) | set(ours) | set(theirs):
        b = base.get(key, _MISSING)
        o = ours.get(key, _MISSING)
        t = theirs.get(key, _MISSING)
        if o == t or b == t:
            continue  # the remote value is already the right one
        if isinstance(b, dict) and isinstance(o, dict) and isinstance(t, dict):
            result[key] = json_merge(b, o, t)
        elif b == o:
            result[key] = t  # remote didn't touch this — keep the player's change
        # else: both sides changed it differently — keep the remote value
    return result


def log(msg: str):
    print(f"[launcher] {msg}", flush=True)


def run(cmd: list) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True)
    except OSError as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def fail(msg: str):
    log("ERROR: " + msg)
    try:
        input("Press Enter to close...")
    except Exception:
        pass
    sys.exit(1)


# ── repo ────────────────────────────────────────────────────────
def find_repo_dir(target: Path) -> Path:
    """Where the game repo lives: the folder itself if it is already a
    clone, otherwise a subfolder for a fresh install."""
    if (target / ".git").exists():
        return target
    return target / INSTALL_SUBDIR


def ensure_clone(repo_dir: Path, repo_url: str):
    if (repo_dir / ".git").exists():
        return
    log(f"Cloning the game into {repo_dir} ...")
    r = run([_GIT, "clone", repo_url, str(repo_dir)])
    if r.returncode != 0:
        fail("Could not clone the repo (is git installed?):\n" + (r.stderr or "").strip()[:500])


# ── tool bootstrap (Git / Python) ───────────────────────────────
def download(url: str, dest: Path):
    """Fetch a file with progress logs. Fails hard when offline."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    log(f"Downloading {url}")
    try:
        with urllib.request.urlopen(url, timeout=60) as resp, open(dest, "wb") as out:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            shown = -10
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    if pct >= shown + 10:
                        shown = pct
                        log(f"  {pct}%")
    except OSError as e:
        try:
            dest.unlink(missing_ok=True)   # don't leave a broken partial file
        except OSError:
            pass
        fail(f"Could not download {url}:\n{e}")
    log("  download finished.")


def wait_for(check, what: str, timeout_s: int, interval_s: float = 2.0):
    """Poll until check() returns something truthy, or the timeout hits.

    Installers usually finish before their process exits, but on slow or
    antivirus-heavy machines files can appear a little later — the launcher
    waits for the tool to actually be ready instead of moving on too early.
    """
    deadline = time.monotonic() + timeout_s
    last_note = 0.0
    while True:
        found = check()
        if found:
            return found
        now = time.monotonic()
        if now >= deadline:
            return None
        if now - last_note >= 15:
            last_note = now
            log(f"Still waiting for {what} ...")
        time.sleep(interval_s)


def add_to_user_path_win(directory: str):
    """Add a folder to the user's PATH (no admin needed). Best effort —
    the launcher calls its tools by full path anyway, this is convenience."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                            winreg.KEY_ALL_ACCESS) as key:
            try:
                current, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current = ""
            current = current or ""
            parts = [p.strip().lower() for p in current.split(";") if p.strip()]
            if directory.lower() in parts:
                return
            new_path = (current.rstrip(";") + ";" if current.strip() else "") + directory
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)

        # Tell other programs the environment changed (no reboot needed)
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        result = ctypes.c_ulong()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
            SMTO_ABORTIFHUNG, 5000, ctypes.byref(result),
        )
        log(f"Added {directory} to PATH.")
    except Exception:
        log("Note: could not add Git to PATH (the launcher will use it directly anyway).")


def find_git(target: Path) -> str | None:
    """A git executable: bundled portable copy first, then PATH."""
    if sys.platform == "win32":
        bundled = target / TOOLS_DIR / "PortableGit" / "cmd" / "git.exe"
        if bundled.exists():
            return str(bundled)
    return shutil.which("git")


def _git_ready(target: Path) -> str | None:
    """The found git, but only once it actually runs."""
    git = find_git(target)
    if not git:
        return None
    return git if run([git, "--version"]).returncode == 0 else None


def ensure_git(target: Path) -> str:
    """Make sure a git executable is available. On Windows a portable copy
    is downloaded and extracted silently (no admin, no installer window)."""
    global _GIT
    git = find_git(target)
    if git:
        _GIT = git
        return git

    if sys.platform != "win32":
        fail("Git was not found.\n"
             "Install it with your package manager (e.g. 'sudo dnf install git') "
             "and run the launcher again.")

    log(f"Git not found — downloading Portable Git {GIT_VERSION} ...")
    url = (f"https://github.com/git-for-windows/git/releases/download/"
           f"v{GIT_VERSION}.windows.1/PortableGit-{GIT_VERSION}-64-bit.7z.exe")
    archive = target / TOOLS_DIR / f"PortableGit-{GIT_VERSION}-64-bit.7z.exe"
    if not archive.exists():
        download(url, archive)

    log("Extracting Git (this takes a moment)...")
    dest = target / TOOLS_DIR / "PortableGit"
    r = run([str(archive), "-o", str(dest), "-y"])
    if r.returncode != 0:
        fail("Could not extract Git:\n" + ((r.stderr or "") + (r.stdout or "")).strip()[:500])
    git = wait_for(lambda: _git_ready(target), "Git", 300)
    if git is None:
        fail("Git did not finish setting up (waited 5 minutes). Run the launcher again.")

    add_to_user_path_win(str(dest / "cmd"))
    log("Git ready.")
    _GIT = git
    return git


def _git(repo_dir: Path, *args) -> subprocess.CompletedProcess:
    return run([_GIT, "-C", str(repo_dir), *args])


def resolve_remote_ref(repo_dir: Path) -> str | None:
    """Remote branch to update from — the tracked upstream if there is one."""
    r = _git(repo_dir, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    ref = (r.stdout or "").strip()
    if r.returncode == 0 and ref.startswith("origin/"):
        return ref
    for candidate in ("origin/main", "origin/master"):
        if _git(repo_dir, "rev-parse", "--verify", "--quiet", candidate).returncode == 0:
            return candidate
    return None


def capture_local_edits(repo_dir: Path) -> list:
    """Snapshot all unstaged edits (e.g. completed missions, code tweaks):
    base = index version, player = worktree version."""
    edits = []
    r = _git(repo_dir, "diff", "--name-only")
    for rel in (r.stdout or "").splitlines():
        rel = rel.strip()
        if not rel:
            continue
        path = repo_dir / rel
        if not path.is_file():
            continue  # locally deleted — let the remote version win
        base = _git(repo_dir, "cat-file", "-p", f":{rel}")
        if base.returncode != 0:
            continue
        try:
            edits.append((path, base.stdout, path.read_text(encoding="utf-8")))
        except OSError:
            continue
    return edits


def reapply_edits(edits: list) -> int:
    """Merge each captured edit back onto the fresh content.
    Returns the number of files that merged with conflicts."""
    conflicts = 0
    for path, base, player in edits:
        if _try_json_merge(path, base, player):
            continue
        conflicts += _line_merge(path, base, player)
    return conflicts


def _try_json_merge(path: Path, base: str, player: str) -> bool:
    """JSON-aware merge: combine field values instead of text lines.
    Returns False when any of the three versions isn't valid JSON."""
    if path.suffix.lower() != ".json":
        return False
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
        base_obj = json.loads(base)
        player_obj = json.loads(player)
    except (OSError, ValueError):
        return False
    merged = json_merge(base_obj, current, player_obj)
    try:
        path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    except OSError:
        return False
    return True


def _line_merge(path: Path, base: str, player: str) -> int:
    """Line-based 3-way merge (git merge-file). Returns 1 on conflict."""
    base_tmp = player_tmp = ""
    try:
        with tempfile.NamedTemporaryFile("w", suffix="_base", delete=False, encoding="utf-8") as tb:
            tb.write(base)
            base_tmp = tb.name
        with tempfile.NamedTemporaryFile("w", suffix="_player", delete=False, encoding="utf-8") as tp:
            tp.write(player)
            player_tmp = tp.name
        # git merge-file <current> <base> <other>:
        #   apply the changes base->other onto current, in place.
        r = run([_GIT, "-C", str(path.parent), "merge-file", str(path), base_tmp, player_tmp])
        return 1 if r.returncode > 0 else 0
    except OSError:
        return 0
    finally:
        if base_tmp:
            Path(base_tmp).unlink(missing_ok=True)
        if player_tmp:
            Path(player_tmp).unlink(missing_ok=True)


def update_repo(repo_dir: Path, repo_url: str):
    """Full startup update: code + content. Local edits are preserved.
    Tolerates being offline."""
    # A folder might be a repo without a remote (e.g. copied by hand) — fix that.
    remotes = _git(repo_dir, "remote")
    if not (remotes.stdout or "").strip():
        _git(repo_dir, "remote", "add", "origin", repo_url)

    log("Checking for updates...")
    if _git(repo_dir, "fetch", "--quiet", "origin").returncode != 0:
        log("Can't reach the remote (offline?) — using the local copy.")
        return

    remote_ref = resolve_remote_ref(repo_dir)
    if remote_ref is None:
        log("No remote branch found — skipping the update.")
        return

    # Keep local edits (e.g. completed missions) safe across the hard update.
    edits = capture_local_edits(repo_dir)

    head = (_git(repo_dir, "rev-parse", "HEAD").stdout or "").strip()
    remote = (_git(repo_dir, "rev-parse", remote_ref).stdout or "").strip()

    # Hard update: working tree + index match the remote exactly
    # (untracked files, e.g. hand-made drafts, are left alone).
    if _git(repo_dir, "reset", "--hard", "--quiet", remote_ref).returncode != 0:
        log("Update failed — continuing with the local copy.")
        return

    if head == remote:
        log("Already up to date.")
    else:
        log("Updated to the latest version.")

    conflicts = reapply_edits(edits)
    if conflicts:
        log(f"Warning: {conflicts} local edit(s) merged with conflicts.")


# ── python environment ─────────────────────────────────────────
def venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def find_python(target: Path) -> str | None:
    """A real interpreter that can build venvs (a frozen exe can't use itself)."""
    if not getattr(sys, "frozen", False):
        return sys.executable  # a real python is running this script
    # frozen exe: look for an installed Python
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "Programs" / "Python"
        if base.is_dir():
            cands = sorted(base.glob("Python3*/python.exe"), reverse=True)
            if cands:
                return str(cands[0])
    for cmd in (["py", "-3"], ["python"], ["python3"]):
        try:
            r = subprocess.run(
                cmd + ["-c", "import sys; print(sys.executable)"],
                capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        exe = (r.stdout or "").strip()
        if r.returncode == 0 and exe and Path(exe).exists():
            return exe
    return None


def _python_ready(target: Path) -> str | None:
    """The found python, but only once it actually runs."""
    py = find_python(target)
    if not py:
        return None
    r = run([py, "-c", "print('ok')"])
    return py if r.returncode == 0 and "ok" in (r.stdout or "") else None


def ensure_python(target: Path) -> str:
    """Make sure a real Python exists. On Windows it is downloaded and
    installed silently (no window, no admin) and added to PATH."""
    py = find_python(target)
    if py:
        return py

    if sys.platform != "win32":
        fail("Python was not found.\n"
             "Install it with your package manager (e.g. 'sudo dnf install python3') "
             "and run the launcher again.")

    log(f"Python not found — downloading Python {PY_VERSION} ...")
    url = f"https://www.python.org/ftp/python/{PY_VERSION}/python-{PY_VERSION}-amd64.exe"
    installer = target / TOOLS_DIR / f"python-{PY_VERSION}-amd64.exe"
    if not installer.exists():
        download(url, installer)

    log("Installing Python quietly (this can take a few minutes)...")
    # /quiet = no installer window; per-user install; PrependPath adds it to PATH
    r = run([str(installer), "/quiet", "InstallAllUsers=0", "PrependPath=1",
             "Include_test=0"])
    if r.returncode not in (0, 3010):   # 3010 = success, reboot recommended
        fail("The Python installer failed:\n" +
             ((r.stderr or "") + (r.stdout or "")).strip()[:500])

    py = wait_for(lambda: _python_ready(target), "Python", 300)
    if py is None:
        fail("Python did not finish installing (waited 5 minutes). Run the launcher again.")
    log("Python ready (added to PATH).")
    return py


def requirements_digest(repo_dir: Path) -> str:
    """Fingerprint of what needs to be installed (requirements.txt or the fallback)."""
    req = repo_dir / "requirements.txt"
    if req.exists():
        return hashlib.sha256(req.read_bytes()).hexdigest()
    return hashlib.sha256(";".join(FALLBACK_REQUIREMENTS).encode()).hexdigest()


def ensure_venv(repo_dir: Path, base: str):
    venv_dir = repo_dir / VENV_NAME
    py = venv_python(venv_dir)

    if not py.exists():
        if venv_dir.exists():
            log("The existing .venv looks broken — recreating it.")
            shutil.rmtree(venv_dir, ignore_errors=True)
        log("Creating the Python environment (.venv)...")
        r = run([base, "-m", "venv", str(venv_dir)])
        if r.returncode != 0 or not py.exists():
            fail("Could not create the Python environment:\n" +
                 ((r.stderr or "") + (r.stdout or "")).strip()[:500])

    # Only run pip when the requirements actually changed since the last install.
    marker = venv_dir / ".requirements.sha256"
    digest = requirements_digest(repo_dir)
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == digest:
        return

    req = repo_dir / "requirements.txt"
    if req.exists():
        cmd = [str(py), "-m", "pip", "install", "-r", str(req)]
    else:
        cmd = [str(py), "-m", "pip", "install", *FALLBACK_REQUIREMENTS]
    log("Downloading required libraries (PySide6)...")
    r = run(cmd)
    if r.returncode != 0:
        # Install failed (offline?) — fine as long as what we need is already there.
        chk = run([str(py), "-c", "import PySide6"])
        if chk.returncode == 0:
            log("Library download failed (offline?), but everything needed is already installed.")
            return
        fail("Could not install the required libraries:\n" +
             ((r.stderr or "") + (r.stdout or "")).strip()[-600:])
    marker.write_text(digest, encoding="utf-8")
    log("Libraries ready.")


# ── app ─────────────────────────────────────────────────────────
def launch_app(repo_dir: Path):
    py = venv_python(repo_dir / VENV_NAME)
    log("Starting Athas...")
    proc = subprocess.run([str(py), str(repo_dir / "main.py")], cwd=str(repo_dir))
    sys.exit(proc.returncode)


def main():
    parser = argparse.ArgumentParser(description="Athas launcher")
    parser.add_argument("--target", help="install folder (default: the launcher's own folder)")
    parser.add_argument("--repo", default=REPO_URL, help="repo url to clone from")
    parser.add_argument("--check", action="store_true", help="set everything up but don't launch")
    args = parser.parse_args()

    if getattr(sys, "frozen", False):
        target = Path(sys.executable).parent
    else:
        target = Path(__file__).resolve().parent
    if args.target:
        target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    ensure_git(target)                     # resolves/installs the git to use
    repo_dir = find_repo_dir(target)
    ensure_clone(repo_dir, args.repo)
    update_repo(repo_dir, args.repo)

    base = ensure_python(target)           # resolves/installs a real python
    ensure_venv(repo_dir, base)

    if args.check:
        log("Everything is set up. Launch cancelled (--check).")
        return
    launch_app(repo_dir)


if __name__ == "__main__":
    main()