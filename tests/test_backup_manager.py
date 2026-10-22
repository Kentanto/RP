"""Tests for athas.backup_manager — timestamped JSON/db backups with 30-day retention."""
import json
from datetime import datetime, timedelta

import pytest

from athas.backup_manager import BackupManager

NOW = datetime(2026, 10, 22, 12, 0, 0)
NOW_FOLDER = "2026-10-22_12-00-00"


@pytest.fixture()
def data_root(tmp_path):
    """A miniature copy of the app's data folders plus noise that must be skipped."""
    (tmp_path / "missions").mkdir()
    (tmp_path / "missions" / "a.json").write_text('{"title": "A"}')
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "skills.json").write_text('{"skills": []}')
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / "system_config.json").write_text('{"player": {}}')
    (tmp_path / "cache" / "inventory.db").write_bytes(b"fake sqlite data")
    (tmp_path / "cache" / ".system_config.json.abc.tmp").write_text("half-written temp file")
    (tmp_path / "draft_missions").mkdir()
    (tmp_path / "draft_missions" / "wip.json").write_text('{"title": "WIP"}')
    # Noise that must never end up inside a backup.
    (tmp_path / "icons").mkdir()
    (tmp_path / "icons" / "bg.png").write_bytes(b"png")
    (tmp_path / "app.py").write_text("print('hi')")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config.json").write_text("{}")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.json").write_text("{}")
    # An earlier backup that must survive untouched.
    old_backup = tmp_path / "backups" / "2026-10-20_09-00-00" / "missions"
    old_backup.mkdir(parents=True)
    (old_backup / "old.json").write_text("{}")
    return tmp_path


def test_backup_copies_json_and_db_keeping_folder_structure(data_root):
    manager = BackupManager(root=data_root)
    target = manager.create_backup(now=NOW)

    assert target == data_root / "backups" / NOW_FOLDER
    assert json.loads((target / "missions" / "a.json").read_text()) == {"title": "A"}
    assert json.loads((target / "draft_missions" / "wip.json").read_text()) == {"title": "WIP"}
    assert json.loads((target / "skills" / "skills.json").read_text()) == {"skills": []}
    assert json.loads((target / "cache" / "system_config.json").read_text()) == {"player": {}}
    assert (target / "cache" / "inventory.db").read_bytes() == b"fake sqlite data"


def test_backup_skips_tooling_folders_and_non_data_files(data_root):
    manager = BackupManager(root=data_root)
    target = manager.create_backup(now=NOW)

    copied = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
    assert copied == {
        "missions/a.json",
        "draft_missions/wip.json",
        "skills/skills.json",
        "cache/system_config.json",
        "cache/inventory.db",
    }
    # The earlier backup was neither overwritten nor re-copied.
    assert (data_root / "backups" / "2026-10-20_09-00-00" / "missions" / "old.json").exists()


def test_every_backup_gets_its_own_folder(data_root):
    manager = BackupManager(root=data_root)
    first = manager.create_backup(now=NOW)
    (data_root / "missions" / "a.json").write_text('{"title": "Updated"}')
    second = manager.create_backup(now=NOW + timedelta(minutes=30))

    assert second.name == "2026-10-22_12-30-00"
    # The first backup keeps the original content untouched.
    assert json.loads((first / "missions" / "a.json").read_text()) == {"title": "A"}
    assert json.loads((second / "missions" / "a.json").read_text()) == {"title": "Updated"}


def test_same_timestamp_gets_a_numbered_folder(data_root):
    manager = BackupManager(root=data_root)
    first = manager.create_backup(now=NOW)
    second = manager.create_backup(now=NOW)

    assert first == data_root / "backups" / NOW_FOLDER
    assert second == data_root / "backups" / f"{NOW_FOLDER}_1"


def test_folders_older_than_30_days_are_deleted(data_root):
    backups = data_root / "backups"
    for name in (
        "2026-09-22_11-59-00",  # 30 days and 1 minute old
        "2026-09-22_12-00-00",  # exactly 30 days old
        "2026-10-22_03-00-00",  # earlier today
        "not-a-date",
    ):
        (backups / name).mkdir(parents=True)

    manager = BackupManager(root=data_root)
    manager.create_backup(now=NOW)

    remaining = {p.name for p in backups.iterdir()}
    assert "2026-09-22_11-59-00" not in remaining  # past 30 days — deleted
    assert "2026-09-22_12-00-00" in remaining       # exactly 30 days — kept
    assert "2026-10-22_03-00-00" in remaining        # today — kept
    assert "not-a-date" in remaining                 # unknown folders untouched
    assert NOW_FOLDER in remaining


def test_empty_root_still_creates_dated_folder(tmp_path):
    manager = BackupManager(root=tmp_path)
    target = manager.create_backup(now=NOW)
    assert target.exists()
