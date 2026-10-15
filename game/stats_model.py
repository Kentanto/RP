"""Character stats: the one module that knows where every number comes from.

Sources, in order:
  * base stats  - stored in the `stats` table, grow on level-up
  * gear        - items equipped into weapon/head/chest/trinket slots
  * artifacts   - the 4 artifact slots; flat stats add, `%` stats multiply

Conventions:
  * Crit Rate / Crit DMG are fractions everywhere (0.05 = 5%).
  * Everything else is a flat number.
"""
import json

from . import db

GEAR_SLOTS = ("weapon", "head", "chest", "trinket")
GEAR_LABELS = {"weapon": "Weapon", "head": "Head", "chest": "Chest",
               "trinket": "Trinket"}

STAT_ORDER = ("HP", "ATK", "DEF", "SPD", "Mana", "Crit Rate", "Crit DMG")

BASE_CRIT_RATE = 0.05   # 5% chance to crit
BASE_CRIT_DMG = 0.50    # crits deal +50% damage

# item stats (data/items.txt) -> canonical stat key
_ITEM_STAT_KEYS = {
    "hp": "HP", "atk": "ATK", "def": "DEF", "spd": "SPD", "mana": "Mana",
    "crit_rate": "Crit Rate", "crit": "Crit Rate", "crit_dmg": "Crit DMG",
}

# artifact stat names -> (canonical key, is_percent)
_ARTIFACT_STATS = {
    "ATK": ("ATK", False), "DEF": ("DEF", False), "HP": ("HP", False),
    "ATK%": ("ATK", True), "DEF%": ("DEF", True), "HP%": ("HP", True),
    "SPD%": ("SPD", True),
    "Crit Rate%": ("Crit Rate", True), "Crit DMG%": ("Crit DMG", True),
}


def format_stat(key, value):
    """Human display for a canonical stat value."""
    if key.startswith("Crit"):
        return f"{value * 100:.1f}%"
    return f"{int(round(value))}"


def sheet():
    """The full character sheet.

    Returns {"level", "xp", "needed", "stats": {key: breakdown}} where each
    breakdown is {"base", "gear", "artifact", "pct", "total"}.
    """
    base = db.get_base_stats()
    entry = {key: {"base": 0, "gear": 0, "artifact": 0, "pct": 0.0}
             for key in STAT_ORDER}
    entry["HP"]["base"] = base["hp"]
    entry["ATK"]["base"] = base["atk"]
    entry["DEF"]["base"] = base["def"]
    entry["SPD"]["base"] = base["spd"]
    entry["Mana"]["base"] = base["mana"]
    entry["Crit Rate"]["base"] = BASE_CRIT_RATE
    entry["Crit DMG"]["base"] = BASE_CRIT_DMG

    # ---- gear
    for _slot, item_key in db.get_equipped_gear().items():
        item = db.get_item_def(item_key)
        if item is None:
            continue
        try:
            stats = json.loads(item["stats"] or "{}")
        except ValueError:
            stats = {}
        for name, value in stats.items():
            key = _ITEM_STAT_KEYS.get(str(name).lower())
            if key:
                entry[key]["gear"] += float(value)

    # ---- artifacts
    equipped = db.get_equipped_artifacts()
    by_id = {row["id"]: row
             for row in db.get_artifacts_by_ids([aid for aid in equipped.values() if aid])}
    for artifact_id in equipped.values():
        row = by_id.get(artifact_id)
        if row is None:
            continue
        pairs = ((row["main_stat"], row["main_stat_value"]),
                 (row["sub_stat1"], row["sub_stat1_value"]),
                 (row["sub_stat2"], row["sub_stat2_value"]))
        for stat, value in pairs:
            if not stat or value is None:
                continue
            target, is_percent = _ARTIFACT_STATS.get(stat, (None, False))
            if target is None:
                continue
            if is_percent:
                entry[target]["pct"] += float(value)
            else:
                entry[target]["artifact"] += float(value)

    # ---- totals
    for key, e in entry.items():
        if key.startswith("Crit"):
            e["total"] = e["base"] + e["gear"] + e["artifact"] + e["pct"]
        else:
            e["total"] = int(round((e["base"] + e["gear"] + e["artifact"])
                                   * (1 + e["pct"])))

    return {
        "level": base["level"],
        "xp": base["xp"],
        "needed": db.xp_for_level(base["level"]),
        "stats": entry,
    }


def breakdown_text(e):
    """Small gray line describing where a stat's total comes from."""
    parts = []
    if e["gear"]:
        parts.append(f"gear +{e['gear']:g}")
    if e["artifact"]:
        parts.append(f"artifacts +{e['artifact']:g}")
    if e["pct"]:
        parts.append(f"+{e['pct'] * 100:.1f}%")
    if not parts:
        return "base"
    return "base " + "  ".join(parts)
