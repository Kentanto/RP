"""
Git Sync — periodically pulls from remote to update local mission files.
Uses subprocess to run git commands.
"""
import os
import subprocess
import threading
from pathlib import Path
from typing import Callable, Any

from PySide6.QtCore import QTimer, QObject, Signal


class GitSyncWorker(QObject):
    """Background git sync worker that emits signals."""

    pull_complete = Signal(bool, str)
    new_files_detected = Signal(list)  # list of file paths

    def __init__(self, repo_path: str, missions_dir: str, interval_ms: int = 30000):
        super().__init__()
        self.repo_path = Path(repo_path)
        self.missions_dir = Path(missions_dir)
        self.interval_ms = interval_ms

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._do_sync)
        self._last_known_files: set = set()

    def start(self):
        # Initial scan
        self._last_known_files = self._scan_mission_files()
        # First pull
        self._do_sync()
        self._timer.start(self.interval_ms)

    def stop(self):
        self._timer.stop()

    def force_pull(self):
        self._do_sync()

    def _scan_mission_files(self) -> set:
        if not self.missions_dir.exists():
            return set()
        return {
            str(p.resolve())
            for p in self.missions_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".txt", ".md", ".json")
        }

    def _do_sync(self):
        """Run git stash -> pull -> restore safely."""
        success = False
        msg = ""
        new_files = []

        try:
            # Check if this is actually a git repo
            if not (self.repo_path / ".git").exists():
                msg = "Not a git repo — running in local-only mode"
                self.pull_complete.emit(False, msg)
                return

            # Stash any local changes (like draft moves)
            self._run_git(["stash", "push", "-m", "auto-stash-before-pull"])

            # Pull latest from remote
            result = self._run_git(["pull", "--no-rebase"])
            success = result.returncode == 0
            msg = result.stdout.strip() if result.stdout else "Pull complete"

            if "Already up to date" in msg:
                msg = "Already up to date"

            # Restore stash
            self._run_git(["stash", "pop"])

            # Check for new mission files
            current_files = self._scan_mission_files()
            new_files = list(current_files - self._last_known_files)
            self._last_known_files = current_files

        except Exception as e:
            msg = str(e)
            success = False

        self.pull_complete.emit(success, msg)
        if new_files:
            self.new_files_detected.emit(new_files)

    def _run_git(self, args: list) -> Any:
        cmd = ["git", "-C", str(self.repo_path)] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.repo_path),
        )
