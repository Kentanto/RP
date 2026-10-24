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
    assert stat_display("worth_attack", 5) == "Attack Point Worth +5"
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
    tiers = set()
    for _ in range(150):
        roll = gen.upgrade_roll("attack", "Rare")
        assert roll["amount"] >= 1
        assert isinstance(roll["high"], bool)
        assert roll["tier"] in ("low", "mid", "high")
        assert roll["high"] == (roll["tier"] == "high")
        tiers.add(roll["tier"])
        # Rare multiplies by 4: low is 4-8, mid is 8-12, high is 12-20.
        assert roll["amount"] >= 4
        assert roll["amount"] <= 20
    assert tiers  # the tier is reported for every roll
    for _ in range(50):
        roll = gen.upgrade_roll("temp_points", "Common")
        assert 1 <= roll["amount"] <= 2


def test_upgrade_rolls_cover_all_three_tiers():
    """Given enough rolls, low, mid and high all appear."""
    gen = ArtifactGenerator()
    seen = set()
    for _ in range(500):
        seen.add(gen.upgrade_roll("attack", "Common")["tier"])
    assert seen == {"low", "mid", "high"}


def test_upgrade_rolls_grow_with_upgrade_level():
    """Higher upgrade levels roll noticeably bigger amounts."""
    gen = ArtifactGenerator()
    low_totals = sum(gen.upgrade_roll("attack", "Common", 0)["amount"] for _ in range(400))
    high_totals = sum(gen.upgrade_roll("attack", "Common", 19)["amount"] for _ in range(400))
    assert high_totals > low_totals


def test_starting_rolls_use_tiers():
    gen = ArtifactGenerator()
    seen = set()
    for _ in range(200):
        stats = gen._roll_stats("Ring", "Mythic")
        for key, value in stats.items():
            if key.startswith("worth_"):
                assert 1 <= value <= 3  # worth points roll small and flat
            seen.add(value)
    assert max(seen) > min(seen)  # tiers produce a spread of values


def test_artifacts_have_no_level():
    """Generation ignores the level argument — artifacts only upgrade."""
    gen = ArtifactGenerator()
    a = gen.generate(rarity="Rare", level=99)
    assert a["level"] == 1
    # Prices ignore the level too — always the rarity's base ± 10%.
    for level in (1, 50, 99):
        assert 360 <= gen.price("Rare", level) <= 440  # 400 base ± 10%


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


def test_drop_template_is_created_and_ignored(tmp_path):
    drops = DropManager(tmp_path / "drops")
    template = drops.drops_dir / "_template.json"
    assert template.exists()
    # The template is never processed or deleted.
    assert drops.collect() == []
    assert template.exists()


def test_drop_underscore_files_are_skipped(tmp_path):
    drops = DropManager(tmp_path / "drops")
    keep = drops.drops_dir / "_keep.json"
    keep.write_text('{"gold": 999}', encoding="utf-8")
    assert drops.collect() == []
    assert keep.exists()


def test_drop_artifacts_and_plain_message(tmp_path):
    drops = DropManager(tmp_path / "drops")
    path = drops.drops_dir / "gift.json"
    path.write_text(json.dumps({
        "artifact_reward": 2,
        "artifact_rarity": "epic",
        "message": "The System smiles upon you.",
    }), encoding="utf-8")
    grants = drops.collect()
    assert len(grants) == 1
    grant = grants[0]
    assert grant["artifact_reward"] == 2
    assert grant["artifact_rarity"] == "Epic"
    assert grant["notification"]["message"] == "The System smiles upon you."
    assert not path.exists()


def _make_manager(tmp_path):
    from athas.inventory_manager import InventoryManager
    return InventoryManager(
        items_dir=tmp_path / "items",
        library_dir=tmp_path / "library",
        cache_dir=tmp_path / "cache",
        rp_root=tmp_path,
    )


def test_reroll_values_keeps_upgrade_level(tmp_path):
    mgr = _make_manager(tmp_path)
    (item,) = mgr.generate_artifacts(count=1, rarity="Rare", level=1, source="mission")
    aid = int(item.uid.split(":", 1)[1])
    for _ in range(3):
        assert mgr.upgrade_artifact(aid) is not None
    fresh = mgr.get_artifact_by_id(aid)
    assert fresh.upgrade_level == 3
    assert len(fresh.upgrade_log) == 3

    rerolled = mgr.reroll_artifact_values(aid)
    assert rerolled is not None
    assert rerolled.upgrade_level == 3        # the level is kept now
    assert len(rerolled.upgrade_log) == 3     # every upgrade re-rolled fresh
    assert set(rerolled.stats) == set(fresh.stats)  # same stat types
    # downgrade still works off the rebuilt log
    result = mgr.unupgrade_artifact(aid)
    assert result is not None
    assert result["item"].upgrade_level == 2


def test_supplies_buy_and_consume(tmp_path):
    mgr = _make_manager(tmp_path)
    assert all(s.count == 0 for s in mgr.get_supplies())
    item = mgr.buy_supply("bandage")
    assert item is not None and item.count == 1
    item = mgr.buy_supply("bandage")
    assert item.count == 2
    item = mgr.consume_supply("bandage")
    assert item.count == 1
    item = mgr.consume_supply("bandage")
    assert item is None                      # stash entry disappears at 0
    assert mgr.consume_supply("medkit") is None  # nothing to consume
    assert mgr.buy_supply("nope") is None    # unknown supply id
