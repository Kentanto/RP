"""
Git Sync — periodically updates only the content folders that matter
(missions, completed_missions, items, icons) from the remote repo.

Instead of pulling the whole repository, this fetches the remote and then
copies ONLY the configured folders from it into the local working tree.
Code, sounds and everything else stay untouched while the app runs — the
launcher handles the full repo update at startup.

Local edits inside the synced folders (e.g. a mission marked as completed)
are snapshotted before the copy and merged back on top of the fresh
content — JSON files are merged field-by-field, so an author edit and a
player edit to the same file coexist instead of colliding.
Files removed on the remote are removed locally too.
"""
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, QObject, Signal

# Folders synced from the remote, relative to the repo root.
DEFAULT_SYNC_PATHS = ("missions", "completed_missions", "items", "icons", "cache", "skills")
AUTOSAVE_PATHS = ("cache", "completed_missions", "missions", "skills")
AUTOSAVE_EXTS = {".json", ".db"}
AUTOSAVE_DELAY_MS = 30000

# File types worth listing for the "new files" signal.
TEXT_EXTS = {".txt", ".md", ".json"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}
SCAN_EXTS = TEXT_EXTS | IMAGE_EXTS

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


class GitSyncWorker(QObject):
    """Background git sync worker that emits signals."""

    pull_complete = Signal(bool, str)
    new_files_detected = Signal(list)  # list of file paths

    def __init__(self, repo_path: str, sync_paths=None, interval_ms: int = 30000):
        super().__init__()
        self.repo_path = Path(repo_path)
        paths = DEFAULT_SYNC_PATHS if sync_paths is None else sync_paths
        self.sync_paths = [str(p).strip().strip("/\\") for p in paths if str(p).strip()]
        self.interval_ms = interval_ms

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._do_sync)
        self._last_known_files: set = set()
        self._autosave_snapshot: dict[str, tuple[int, int]] = {}
        self._pending_autosave_paths: set[str] = set()
        self._ignored_paths: dict[str, bool] = {}  # repo-relative path -> git-ignored?
        self._push_pending = False

        self._autosave_watch = QTimer(self)
        self._autosave_watch.timeout.connect(self._poll_autosave_changes)
        self._autosave_debounce = QTimer(self)
        self._autosave_debounce.setSingleShot(True)
        self._autosave_debounce.timeout.connect(self._commit_local_changes)

    # ── lifecycle ──────────────────────────────────────────────
    def start(self):
        # Initial scan
        self._last_known_files = self._scan_sync_files()
        if not (self.repo_path / ".git").exists() or self._resolve_remote_ref() is None:
            self._do_sync()
            self._timer.start(self.interval_ms)
            return
        self._autosave_snapshot = self._scan_autosave_files()
        self._pending_autosave_paths.update(self._git_changed_autosave_paths())
        if self._pending_autosave_paths:
            self._autosave_debounce.start(AUTOSAVE_DELAY_MS)
        else:
            self._do_sync()
            self._autosave_snapshot = self._scan_autosave_files()
        self._timer.start(self.interval_ms)
        self._autosave_watch.start(1000)

    def stop(self):
        self._timer.stop()
        self._autosave_watch.stop()
        self._autosave_debounce.stop()

    def force_pull(self):
        self._do_sync()

    def _scan_sync_files(self) -> set:
        """List all files inside the sync folders worth watching."""
        files: set = set()
        for name in self.sync_paths:
            folder = self.repo_path / name
            if not folder.is_dir():
                continue
            for p in folder.rglob("*"):
                if p.is_file() and p.suffix.lower() in SCAN_EXTS:
                    files.add(str(p.resolve()))
        return files

    def _scan_autosave_files(self) -> dict[str, tuple[int, int]]:
        files = {}
        for name in AUTOSAVE_PATHS:
            folder = self.repo_path / name
            if not folder.is_dir():
                continue
            for path in folder.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in AUTOSAVE_EXTS:
                    continue
                rel = path.relative_to(self.repo_path).as_posix()
                if self._git_ignored(rel):
                    continue  # deliberately unsynced files never block the autosave
                try:
                    stat = path.stat()
                    files[rel] = (stat.st_mtime_ns, stat.st_size)
                except OSError:
                    continue
        return files

    def _git_ignored(self, rel_path: str) -> bool:
        """True when git deliberately ignores the file (e.g. the local
        seen-missions cache). Results are cached — .gitignore rarely changes."""
        if rel_path not in self._ignored_paths:
            try:
                r = self._run_git(["check-ignore", "--", rel_path])
                ignored = r.returncode == 0
            except OSError:
                ignored = False  # git unavailable — watch everything as before
            self._ignored_paths[rel_path] = ignored
        return self._ignored_paths[rel_path]

    def _poll_autosave_changes(self):
        current = self._scan_autosave_files()
        changed = {
            path for path in self._autosave_snapshot.keys() | current.keys()
            if self._autosave_snapshot.get(path) != current.get(path)
        }
        self._autosave_snapshot = current
        if changed:
            self._pending_autosave_paths.update(changed)
            self._autosave_debounce.start(AUTOSAVE_DELAY_MS)

    def _git_changed_autosave_paths(self) -> set[str]:
        result = self._run_git([
            "status", "--porcelain=v1", "-z", "--untracked-files=all", "--",
            *AUTOSAVE_PATHS,
        ])
        changed = set()
        remote_ref = self._resolve_remote_ref()
        for record in (result.stdout or "").split("\0"):
            if len(record) < 4:
                continue
            index_status, worktree_status = record[0], record[1]
            path = record[3:]
            if Path(path).suffix.lower() not in AUTOSAVE_EXTS:
                continue
            if record.startswith("??") or worktree_status != " ":
                changed.add(path)
            elif index_status != " ":
                remote_diff = self._run_git(["diff", "--quiet", remote_ref or "HEAD", "--", path])
                if remote_diff.returncode != 0:
                    changed.add(path)
        return changed

    def _commit_local_changes(self):
        paths = sorted(self._pending_autosave_paths)
        if not paths:
            return

        changed = self._git_changed_autosave_paths()
        paths = [path for path in paths if path in changed]
        if not paths:
            self._pending_autosave_paths.clear()
            self._autosave_snapshot = self._scan_autosave_files()
            return

        added = self._run_git(["add", "-A", "--", *paths])
        if added.returncode != 0:
            self._autosave_failed("Could not stage local changes")
            return
        staged = self._run_git(["diff", "--cached", "--quiet", "--", *paths])
        if staged.returncode == 0:
            self._pending_autosave_paths.clear()
            self._autosave_snapshot = self._scan_autosave_files()
            return

        commit = self._run_git(["commit", "--only", "-m", "save file", "--", *paths])
        if commit.returncode != 0:
            message = (commit.stderr or commit.stdout or "Git commit failed").strip().splitlines()
            self._autosave_failed(message[-1] if message else "Git commit failed")
            return

        self._pending_autosave_paths.clear()
        self._autosave_snapshot = self._scan_autosave_files()
        self._push_pending = True
        if self._push_local_changes():
            self.pull_complete.emit(True, "Local changes saved and pushed")

    def _push_local_changes(self) -> bool:
        result = self._run_git(["push"])
        if result.returncode == 0:
            self._push_pending = False
            return True

        fetch = self._run_git(["fetch", "--quiet", "origin"])
        remote_ref = self._resolve_remote_ref() if fetch.returncode == 0 else None
        if remote_ref is not None:
            rebase = self._run_git(["rebase", "--autostash", remote_ref])
            if rebase.returncode == 0:
                result = self._run_git(["push"])
                if result.returncode == 0:
                    self._push_pending = False
                    return True
            else:
                self._run_git(["rebase", "--abort"])
                result = rebase

        message = (result.stderr or result.stdout or "Git push failed").strip().splitlines()
        self.pull_complete.emit(False, message[-1] if message else "Git push failed")
        return False

    def _autosave_failed(self, message: str):
        self.pull_complete.emit(False, message)
        self._autosave_debounce.start(AUTOSAVE_DELAY_MS)

    # ── sync ───────────────────────────────────────────────────
    def _do_sync(self):
        """Fetch the remote and copy only the sync folders from it."""
        self._poll_autosave_changes()
        if self._push_pending and not self._push_local_changes():
            return
        if self._pending_autosave_paths:
            self.pull_complete.emit(False, "Local changes waiting to be saved")
            return

        success = False
        msg = ""
        new_files: list = []
        removed = 0

        try:
            # Check if this is actually a git repo
            if not (self.repo_path / ".git").exists():
                self.pull_complete.emit(False, "Not a git repo — running in local-only mode")
                return

            remote_ref = self._resolve_remote_ref()
            if remote_ref is None:
                self.pull_complete.emit(False, "No remote configured — running in local-only mode")
                return

            fetch = self._run_git(["fetch", "--quiet", "origin"])
            if fetch.returncode != 0:
                self.pull_complete.emit(False, "Sync failed (offline?)")
                return

            # Only sync folders that actually exist on the remote
            targets = self._paths_on_remote(remote_ref)
            if not targets:
                self.pull_complete.emit(True, "Content up to date")
                return

            # Snapshot local edits inside the sync folders (e.g. completed
            # missions) so they can be merged back onto the fresh content.
            edits = self._capture_local_edits()

            # Copy ONLY the sync folders from the remote into working tree + index
            self._run_git(["restore", "--source", remote_ref, "--worktree", "--staged", "--", *targets])

            # Merge the local edits back on top of the new remote content
            conflicts = self._reapply_edits(edits)

            # Track files the remote added, so deletions sync later
            self._track_new_remote_files(remote_ref, targets)

            # Remove files that were deleted on the remote
            removed = self._remove_deleted_files(remote_ref)

            # Check for new files
            current_files = self._scan_sync_files()
            new_files = sorted(current_files - self._last_known_files)
            self._last_known_files = current_files

            success = True
            if new_files or removed:
                msg = f"Content synced ({len(new_files)} new, {removed} removed)"
            else:
                msg = "Content up to date"
            if conflicts:
                msg += f" — {conflicts} file(s) merged with conflicts"
            self._autosave_snapshot = self._scan_autosave_files()

        except Exception as e:
            msg = str(e)
            success = False

        self.pull_complete.emit(success, msg)
        if new_files:
            self.new_files_detected.emit(new_files)

    # ── helpers ────────────────────────────────────────────────
    def _resolve_remote_ref(self) -> str | None:
        """Remote branch to sync from — the tracked upstream if there is one."""
        r = self._run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
        ref = (r.stdout or "").strip()
        if r.returncode == 0 and ref.startswith("origin/"):
            return ref
        for candidate in ("origin/main", "origin/master"):
            c = self._run_git(["rev-parse", "--verify", "--quiet", candidate])
            if c.returncode == 0:
                return candidate
        return None

    def _paths_on_remote(self, remote_ref: str) -> list:
        """Filter the sync folders down to the ones present on the remote."""
        r = self._run_git(["ls-tree", "--name-only", remote_ref])
        top = {line.strip() for line in (r.stdout or "").splitlines() if line.strip()}
        return [p for p in self.sync_paths if p.split("/")[0] in top]

    def _capture_local_edits(self) -> list:
        """Snapshot unstaged edits inside the sync folders.

        For each edited file we remember the index version (the base the
        edit was made on) and the worktree version (the player's edit).
        """
        r = self._run_git(["diff", "--name-only", "--", *self.sync_paths])
        edits = []
        for rel in (r.stdout or "").splitlines():
            rel = rel.strip()
            if not rel:
                continue
            path = self.repo_path / rel
            if not path.is_file():
                continue  # locally deleted — let the remote version win
            base = self._run_git(["cat-file", "-p", f":{rel}"])
            if base.returncode != 0:
                continue
            try:
                edits.append({
                    "path": path,
                    "base": base.stdout,
                    "player": path.read_text(encoding="utf-8"),
                })
            except OSError:
                continue
        return edits

    def _reapply_edits(self, edits: list) -> int:
        """Merge each captured edit back onto the fresh content.

        Returns the number of files that merged with conflicts.
        """
        conflicts = 0
        for e in edits:
            if self._try_json_merge(e):
                continue
            conflicts += self._line_merge(e)
        return conflicts

    def _try_json_merge(self, e: dict) -> bool:
        """JSON-aware merge: combine field values instead of text lines, so
        an author change and a player change to the same file coexist.
        Returns False when any of the three versions isn't valid JSON."""
        if e["path"].suffix.lower() != ".json":
            return False
        try:
            current = json.loads(e["path"].read_text(encoding="utf-8"))
            base = json.loads(e["base"])
            player = json.loads(e["player"])
        except (OSError, ValueError):
            return False
        merged = json_merge(base, current, player)
        try:
            e["path"].write_text(json.dumps(merged, indent=2), encoding="utf-8")
        except OSError:
            return False
        return True

    def _line_merge(self, e: dict) -> int:
        """Line-based 3-way merge (git merge-file). Returns 1 on conflict."""
        base_tmp = player_tmp = ""
        try:
            with tempfile.NamedTemporaryFile("w", suffix="_base", delete=False, encoding="utf-8") as tb:
                tb.write(e["base"])
                base_tmp = tb.name
            with tempfile.NamedTemporaryFile("w", suffix="_player", delete=False, encoding="utf-8") as tp:
                tp.write(e["player"])
                player_tmp = tp.name
            # git merge-file <current> <base> <other>:
            #   apply the changes base->other onto current, in place.
            r = self._run_git(["merge-file", str(e["path"]), base_tmp, player_tmp])
            return 1 if r.returncode > 0 else 0
        except OSError:
            return 0
        finally:
            if base_tmp:
                Path(base_tmp).unlink(missing_ok=True)
            if player_tmp:
                Path(player_tmp).unlink(missing_ok=True)

    def _track_new_remote_files(self, remote_ref: str, targets: list):
        """Add files the remote added to the index, so a later deletion
        on the remote can remove them again."""
        r = self._run_git(["ls-tree", "-r", "--name-only", remote_ref, "--", *targets])
        remote_files = [line.strip() for line in (r.stdout or "").splitlines() if line.strip()]
        if not remote_files:
            return
        r = self._run_git(["ls-files", "--", *targets])
        known = {line.strip() for line in (r.stdout or "").splitlines() if line.strip()}
        for rel in remote_files:
            if rel not in known:
                self._run_git(["add", "--", rel])

    def _remove_deleted_files(self, remote_ref: str) -> int:
        """Delete local (tracked) files inside the sync folders the remote no longer has."""
        # Note: this checks ALL sync folders, not just the ones still present on
        # the remote — a folder emptied on the remote is invisible to ls-tree.
        r = self._run_git(["ls-files", "--", *self.sync_paths])
        local_tracked = {line.strip() for line in (r.stdout or "").splitlines() if line.strip()}
        if not local_tracked:
            return 0

        r = self._run_git(["ls-tree", "-r", "--name-only", remote_ref, "--", *self.sync_paths])
        remote_files = {line.strip() for line in (r.stdout or "").splitlines() if line.strip()}

        removed = 0
        for rel in sorted(local_tracked - remote_files):
            target = self.repo_path / rel
            if target.is_file():
                try:
                    target.unlink()
                    self._run_git(["rm", "--cached", "--quiet", "--", rel])
                    removed += 1
                except OSError:
                    continue
        return removed

    def _run_git(self, args: list) -> Any:
        cmd = ["git", "-C", str(self.repo_path)] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.repo_path),
        )
