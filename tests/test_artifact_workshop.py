"""Tests for the artifact workshop: special stats, upgrades, rerolls,
equipment slots, and the drops-folder parser."""
import json

import pytest

from athas.artifact_generator import (
    ArtifactGenerator, is_worth_stat, stat_display,
    MAX_UPGRADE_LEVEL, EQUIP_SLOTS,
)
from athas import equip
from athas.drop_manager import DropManager


class FakeConfig:
    """Just enough of ConfigManager for the equip helpers."""

    def __init__(self):
        self.data = {"player": {"equipped_artifacts": []}}

    def get(self, section, key, default=None):
        return self.data.get(section, {}).get(key, default)

    def set(self, section, key, value, save=True):
        self.data.setdefault(section, {})[key] = value


def test_worth_stat_detection():
    assert is_worth_stat("worth_attack")
    assert is_worth_stat("worth_crit_chance") is False  # not a main stat
    assert is_worth_stat("attack") is False
    assert is_worth_stat("temp_points") is False


def test_stat_display_formats_every_kind():
    assert stat_display("health", 12) == "Health +12"
    assert stat_display("crit_chance", 4) == "Crit Chance +4%"
    assert stat_display("worth_attack", 5) == "Attack Point Worth +5 DG"
    assert stat_display("temp_points", 3) == "Temp Points +3"


def test_rolls_can_include_special_stats():
    """Given enough rolls, special stats (worth / temp points) appear."""
    gen = ArtifactGenerator()
    seen = set()
    for _ in range(200):
        stats = gen._roll_stats("Ring", "Mythic", 1)
        seen.update(stats.keys())
    assert any(is_worth_stat(k) for k in seen)
    assert "temp_points" in seen


def test_upgrade_costs_scale_and_refund_half():
    gen = ArtifactGenerator()
    first = gen.upgrade_cost("Common", 0)
    later = gen.upgrade_cost("Common", 10)
    mythic = gen.upgrade_cost("Mythic", 0)
    assert first >= 1
    assert later > first
    assert mythic > first
    assert gen.unupgrade_refund("Common", 100) == 50
    # Rerolls cost a chunk of the rarity base price and are not refundable.
    assert gen.reroll_stats_cost("Rare") == 200
    assert gen.reroll_values_cost("Rare") == 300


def test_upgrade_roll_bounds():
    gen = ArtifactGenerator()
    for _ in range(50):
        roll = gen.upgrade_roll("attack", "Rare")
        assert roll["amount"] >= 1
        assert isinstance(roll["high"], bool)
        # Rare multiplies by 4: low is 4-8, high is 12-20.
        assert roll["amount"] >= 4
        assert roll["amount"] <= 20
    for _ in range(50):
        roll = gen.upgrade_roll("temp_points", "Common")
        assert 1 <= roll["amount"] <= 2


def test_reroll_values_keeps_the_same_stat_types():
    gen = ArtifactGenerator()
    stats = {"attack": 10, "worth_speed": 2}
    rerolled = gen.reroll_stat_values(stats, "Rare", 1)
    assert set(rerolled.keys()) == {"attack", "worth_speed"}
    assert rerolled["attack"] >= 1


def test_equip_slots_are_limited_to_five():
    cfg = FakeConfig()
    for i in range(EQUIP_SLOTS):
        assert equip.equip(cfg, i) is True
    for i in range(EQUIP_SLOTS, 10):
        assert equip.equip(cfg, i) is False
    ids = equip.equipped_ids(cfg)
    assert len(ids) == EQUIP_SLOTS
    assert ids == [0, 1, 2, 3, 4]
    assert equip.unequip(cfg, 2) is True
    assert equip.equipped_ids(cfg) == [0, 1, 3, 4]
    assert equip.equip(cfg, 9) is True
    assert len(equip.equipped_ids(cfg)) == EQUIP_SLOTS


def test_prune_equipped_removes_missing_ids():
    cfg = FakeConfig()
    equip.set_equipped(cfg, [1, 2, 3])
    removed = equip.prune_equipped(cfg, [2])
    assert removed == [1, 3]
    assert equip.equipped_ids(cfg) == [2]


def test_drop_json_file(tmp_path):
    drops = DropManager(tmp_path / "drops")
    path = drops.drops_dir / "gift.json"
    path.write_text(json.dumps({
        "gold": 100, "skill_points": 1, "con points": 2,
        "notification": {"title": "Hello", "message": "Well done."},
    }), encoding="utf-8")
    grants = drops.collect()
    assert len(grants) == 1
    grant = grants[0]
    assert grant["gold"] == 100
    assert grant["skill_points"] == 1
    assert grant["constellation_points"] == 2
    assert grant["notification"]["title"] == "Hello"
    assert not path.exists()  # consumed


def test_drop_txt_file(tmp_path):
    drops = DropManager(tmp_path / "drops")
    path = drops.drops_dir / "note.txt"
    path.write_text(
        "gold: 50\ntemp points = 3\nnotification: The System is watching.\n",
        encoding="utf-8",
    )
    grants = drops.collect()
    assert len(grants) == 1
    grant = grants[0]
    assert grant["gold"] == 50
    assert grant["temp_points"] == 3
    assert grant["notification"]["message"] == "The System is watching."
    assert not path.exists()


def test_bad_drop_files_are_consumed(tmp_path):
    drops = DropManager(tmp_path / "drops")
    bad = drops.drops_dir / "broken.json"
    bad.write_text("{not json at all", encoding="utf-8")
    assert drops.collect() == []
    assert not bad.exists()
