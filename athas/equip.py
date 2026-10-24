"""
Equipment — the artifact loadout.

Artifacts only apply their stats while equipped, and the player has
EQUIP_SLOTS (5) slots. The equipped artifact ids live in the player config
(cache/system_config.json) so the loadout syncs through git like every
other player value.

This module holds the small helpers every caller shares so the equip list
is always read and written the same way.
"""
from athas.artifact_generator import EQUIP_SLOTS

_KEY = "equipped_artifacts"


def equipped_ids(config) -> list:
    """The equipped artifact ids, as a clean list of ints (order = slot order)."""
    raw = config.get("player", _KEY, []) if config is not None else []
    ids: list = []
    if isinstance(raw, dict):
        raw = list(raw.values())
    for value in raw or []:
        try:
            aid = int(value)
        except (TypeError, ValueError):
            continue
        if aid not in ids:
            ids.append(aid)
    return ids[:EQUIP_SLOTS]


def set_equipped(config, ids) -> list:
    """Store the equipped ids (clamped to the slot limit, order preserved)."""
    clean = _clean(ids)[:EQUIP_SLOTS]
    if config is not None:
        config.set("player", _KEY, clean)
    return clean


def _clean(ids) -> list:
    out: list = []
    for value in ids or []:
        try:
            aid = int(value)
        except (TypeError, ValueError):
            continue
        if aid not in out:
            out.append(aid)
    return out


def is_equipped(config, artifact_id) -> bool:
    try:
        aid = int(artifact_id)
    except (TypeError, ValueError):
        return False
    return aid in equipped_ids(config)


def equip(config, artifact_id) -> bool:
    """Fill the next free slot. Returns False when the loadout is full."""
    ids = equipped_ids(config)
    try:
        aid = int(artifact_id)
    except (TypeError, ValueError):
        return False
    if aid in ids:
        return True
    if len(ids) >= EQUIP_SLOTS:
        return False
    ids.append(aid)
    set_equipped(config, ids)
    return True


def unequip(config, artifact_id) -> bool:
    """Remove one artifact from the loadout. Returns True when it was on."""
    ids = equipped_ids(config)
    try:
        aid = int(artifact_id)
    except (TypeError, ValueError):
        return False
    if aid not in ids:
        return False
    ids.remove(aid)
    set_equipped(config, ids)
    return True


def prune_equipped(config, existing_ids) -> list:
    """Drop equipped ids that no longer exist in the inventory.

    Returns the (possibly empty) list of ids that were removed."""
    existing = set()
    for value in existing_ids or []:
        try:
            existing.add(int(value))
        except (TypeError, ValueError):
            continue
    ids = equipped_ids(config)
    kept = [aid for aid in ids if aid in existing]
    removed = [aid for aid in ids if aid not in existing]
    if removed:
        set_equipped(config, kept)
    return removed
