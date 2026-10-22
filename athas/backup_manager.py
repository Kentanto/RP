"""
Athas — Backup Manager.

On startup and every 30 minutes the app copies every ``*.json`` data file
(plus any ``*.db`` database such as ``cache/inventory.db``) into a fresh
``backups/<date_time>/`` folder. Inside it each file keeps the folder it
came from, so a mission lands at
``backups/2026-10-22_15-30-00/missions/<file>.json`` and the player config
at ``backups/2026-10-22_15-30-00/cache/system_config.json``.

Every backup gets its own folder — no backup ever overwrites an earlier
one — and folders older than 30 days are deleted automatically.
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# How often the running app refreshes the backup (milliseconds).
BACKUP_INTERVAL_MS = 30 * 60 * 1000
# How long a backup folder survives before it is deleted.
BACKUP_RETENTION_DAYS = 30

# File types that hold player data (matches the git autosave watch list).
BACKUP_SUFFIXES = {".json", ".db"}

# Folders that never hold player data worth backing up.
EXCLUDED_DIRS = {"backups", ".git", ".venv", "__pycache__", ".pytest_cache"}

_FOLDER_FORMAT = "%Y-%m-%d_%H-%M-%S"


class BackupManager:
    """Copies JSON/db data files into timestamped backup folders and prunes old ones."""

    def __init__(self, root: Path, backups_dir: Path | None = None):
        self.root = Path(root)
        self.backups_dir = Path(backups_dir) if backups_dir is not None else self.root / "backups"

    def create_backup(self, now: datetime | None = None) -> Path:
        """Snapshot every data file into a new ``backups/<date_time>/`` folder.

        Every call creates its own folder, so no backup ever overwrites an
        earlier one. Returns the folder the files were copied into.
        """
        now = now or datetime.now()
        target_dir = self._reserve_target_dir(now)
        for src in self._collect_files():
            dest = target_dir / src.relative_to(self.root)
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
            except OSError:
                continue  # unreadable or locked file — skip it, keep the rest
        self._cleanup_old_folders(now)
        return target_dir

    def _reserve_target_dir(self, now: datetime) -> Path:
        """Pick a fresh folder for this backup, numbering rare collisions."""
        base = now.strftime(_FOLDER_FORMAT)
        target = self.backups_dir / base
        suffix = 0
        while target.exists():
            suffix += 1
            target = self.backups_dir / f"{base}_{suffix}"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _collect_files(self) -> list[Path]:
        """Every ``*.json``/``*.db`` file under the root, skipping tooling folders."""
        files: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            # Never descend into backups, git, or environment folders.
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
            for name in filenames:
                if Path(name).suffix.lower() in BACKUP_SUFFIXES:
                    files.append(Path(dirpath) / name)
        return sorted(files)

    def _cleanup_old_folders(self, now: datetime) -> list[Path]:
        """Delete backup folders older than ``BACKUP_RETENTION_DAYS`` days."""
        removed: list[Path] = []
        if not self.backups_dir.exists():
            return removed
        cutoff = now - timedelta(days=BACKUP_RETENTION_DAYS)
        for entry in sorted(self.backups_dir.iterdir()):
            try:
                # Accepts plain folders and numbered collisions ("..._1").
                folder_time = datetime.strptime(entry.name[:19], _FOLDER_FORMAT)
            except ValueError:
                continue  # not a backup folder — leave it alone
            if folder_time < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
                removed.append(entry)
        return removed
