"""All database access for Athas.

One module, no circular imports. Every function opens a short-lived
connection via _connect(), so the rest of the code never touches sqlite3.

Skill progress is stored as JSON (the old code stored Python repr strings
and loaded them back with eval(), which was unsafe and fragile —
_parse_upgrade_names() tolerates both formats).
"""
import ast
import json
import os
import random
import sqlite3
import time
from contextlib import contextmanager

from . import content, settings


@contextmanager
def _connect():
    """Short-lived DB connection that always closes.

    Note: `with sqlite3.connect(...)` alone only manages the transaction —
    it never closes the connection, which leaked handles everywhere.
    """
    os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row     # int-indexed like tuples, plus row["col"]
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------------------------------------------- schema

def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def initialize_database():
    os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
    with _connect() as conn:
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    main_stat TEXT NOT NULL,
                    main_stat_value REAL NOT NULL,
                    sub_stat1 TEXT,
                    sub_stat1_value REAL,
                    sub_stat2 TEXT,
                    sub_stat2_value REAL,
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    max_level INTEGER DEFAULT 20,
                    def_key TEXT DEFAULT 'relic')""")

        c.execute("""CREATE TABLE IF NOT EXISTS stats
                     (id INTEGER PRIMARY KEY, level INTEGER, hp INTEGER,
                      atk INTEGER, def INTEGER, spd INTEGER, mana INTEGER)""")

        c.execute("""CREATE TABLE IF NOT EXISTS points
                     (id INTEGER PRIMARY KEY, points INTEGER, last_updated INTEGER,
                      artifact_points INTEGER DEFAULT 0)""")

        c.execute("""CREATE TABLE IF NOT EXISTS skills
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL,
                      level INTEGER DEFAULT 0,
                      active_upgrades TEXT,
                      unlocked_paths TEXT)""")

        c.execute("""CREATE TABLE IF NOT EXISTS equipped (
                    slot INTEGER PRIMARY KEY,
                    artifact_id INTEGER)""")
        for slot in range(1, 5):
            c.execute("SELECT COUNT(*) FROM equipped WHERE slot=?", (slot,))
            if c.fetchone()[0] == 0:
                c.execute("INSERT INTO equipped (slot, artifact_id) VALUES (?, NULL)", (slot,))

        # ---- item/artifact definitions (source: data/*.txt, synced below)
        c.execute("""CREATE TABLE IF NOT EXISTS item_defs (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'misc',
                    category TEXT NOT NULL DEFAULT 'normal',
                    rarity TEXT NOT NULL DEFAULT 'common',
                    slot TEXT,
                    stats TEXT NOT NULL DEFAULT '{}',
                    price INTEGER DEFAULT 0,
                    sell_price INTEGER DEFAULT 0,
                    shop INTEGER DEFAULT 0,
                    stock INTEGER DEFAULT -1,
                    stackable INTEGER DEFAULT 0,
                    max_stack INTEGER DEFAULT 1,
                    icon TEXT DEFAULT '',
                    color TEXT DEFAULT '200,200,200',
                    description TEXT DEFAULT '')""")

        c.execute("""CREATE TABLE IF NOT EXISTS artifact_defs (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    rarity TEXT NOT NULL DEFAULT 'common',
                    weight INTEGER DEFAULT 1,
                    icon TEXT DEFAULT 'gem',
                    color TEXT DEFAULT '200,200,200',
                    max_level INTEGER DEFAULT 20,
                    main_stats TEXT NOT NULL DEFAULT '{}',
                    sub_stats TEXT NOT NULL DEFAULT '{}',
                    lore TEXT DEFAULT '')""")

        # ---- inventory (keyed by item_defs.key)
        existing = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='inventory'"
        ).fetchone()
        if existing and "item_key" not in _columns(conn, "inventory"):
            c.execute("DROP TABLE inventory")   # old item_id-based rows can't map
        c.execute("""CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_key TEXT NOT NULL UNIQUE,
                    quantity INTEGER DEFAULT 1,
                    acquired_date INTEGER DEFAULT (strftime('%s', 'now')))""")

        # legacy tables from the pre-revamp item system
        c.execute("DROP TABLE IF EXISTS items")
        c.execute("DROP TABLE IF EXISTS shop_inventory")

        # existing artifact rows predate archetype defs
        if "def_key" not in _columns(conn, "artifacts"):
            c.execute("ALTER TABLE artifacts ADD COLUMN def_key TEXT DEFAULT 'relic'")

        # character stats: xp column + gear equipment
        if "xp" not in _columns(conn, "stats"):
            c.execute("ALTER TABLE stats ADD COLUMN xp INTEGER DEFAULT 0")
        c.execute("""CREATE TABLE IF NOT EXISTS equipped_gear (
                    slot TEXT PRIMARY KEY,
                    item_key TEXT)""")

        c.execute("SELECT COUNT(*) FROM skills")
        if c.fetchone()[0] == 0:
            from . import skills_data
            for skill in skills_data.SKILLS:
                c.execute("INSERT INTO skills (name, level, active_upgrades, unlocked_paths) "
                          "VALUES (?, 0, '[]', '[]')", (skill.name,))

        c.execute("SELECT COUNT(*) FROM points")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO points (points, last_updated) VALUES (?, ?)",
                      (600, int(time.time())))

        # ---- missions (source: data/missions.txt, synced below)
        c.execute("""CREATE TABLE IF NOT EXISTS missions (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    mtype TEXT NOT NULL,
                    target INTEGER DEFAULT 1,
                    reward_points INTEGER DEFAULT 0,
                    reward_xp INTEGER DEFAULT 0,
                    reward_artifact_points INTEGER DEFAULT 0,
                    progress INTEGER DEFAULT 0,
                    claimed INTEGER DEFAULT 0)""")

        # character resources: current HP/mana + regen bookkeeping
        # (-1 = "never read", the first read starts the pool at full)
        for column, default in (("hp_current", -1), ("mana_current", -1),
                               ("regen_at", 0)):
            if column not in _columns(conn, "stats"):
                c.execute(f"ALTER TABLE stats ADD COLUMN {column} "
                          f"INTEGER DEFAULT {default}")

    sync_item_defs()
    sync_artifact_defs()
    sync_missions()



# --------------------------------------------------------------- points

def get_current_points():
    """Skill/mini-game points. Accrues +1 per minute offline, capped at 600."""
    with _connect() as conn:
        row = conn.execute("SELECT points, last_updated FROM points").fetchone()
        if row is None:
            return 600
        points, last_updated = row
        elapsed_minutes = (int(time.time()) - last_updated) // 60
        if elapsed_minutes > 0:
            points = min(600, points + elapsed_minutes)
            conn.execute("UPDATE points SET points = ?, last_updated = ?",
                         (points, int(time.time())))
            conn.commit()
        return points


def update_points(new_points):
    with _connect() as conn:
        conn.execute("UPDATE points SET points = ?, last_updated = ?",
                     (new_points, int(time.time())))
        conn.commit()


def add_points(amount):
    update_points(get_current_points() + amount)


def subtract_points(cost):
    """Spend points. Returns False (and changes nothing) if not enough."""
    with _connect() as conn:
        row = conn.execute("SELECT points FROM points").fetchone()
        current = row[0] if row else 0
        if current < cost:
            return False
        conn.execute("UPDATE points SET points = ?, last_updated = ?",
                     (current - cost, int(time.time())))
        conn.commit()
        return True


def get_artifact_points():
    with _connect() as conn:
        row = conn.execute("SELECT artifact_points FROM points").fetchone()
        return row[0] if row else 0


def update_artifact_points(points):
    with _connect() as conn:
        conn.execute("UPDATE points SET artifact_points = ?", (points,))
        conn.commit()


def spend_artifact_points(amount):
    current = get_artifact_points()
    if current >= amount:
        update_artifact_points(current - amount)
        return True
    return False


def add_artifact_points(amount):
    current = get_artifact_points()
    update_artifact_points(current + amount)
    return current + amount


# ---------------------------------------------------------- character sheet

def xp_for_level(level):
    """XP needed to advance from `level` to the next one."""
    return 100 + (level - 1) * 50


def get_base_stats():
    """Persisted base stats; the row is created on first read."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT level, xp, hp, atk, def, spd, mana FROM stats WHERE id=1").fetchone()
        if row is None:
            conn.execute("INSERT INTO stats (id, level, hp, atk, def, spd, mana, xp) "
                         "VALUES (1, 1, 100, 10, 5, 10, 50, 0)")
            conn.commit()
            row = conn.execute(
                "SELECT level, xp, hp, atk, def, spd, mana FROM stats WHERE id=1").fetchone()
    return dict(row)


def add_xp(amount):
    """Grant XP. Level-ups grow the base stats.

    Returns {"level", "xp", "needed", "levels_gained"} or None when
    nothing was granted.
    """
    if amount <= 0:
        return None
    with _connect() as conn:
        row = conn.execute("SELECT level, xp FROM stats WHERE id=1").fetchone()
        if row is None:
            conn.execute("INSERT INTO stats (id, level, hp, atk, def, spd, mana, xp) "
                         "VALUES (1, 1, 100, 10, 5, 10, 50, 0)")
            row = conn.execute("SELECT level, xp FROM stats WHERE id=1").fetchone()
        level, xp = row["level"], row["xp"]
        xp += amount
        levels_gained = 0
        while xp >= xp_for_level(level):
            xp -= xp_for_level(level)
            level += 1
            levels_gained += 1
            conn.execute("UPDATE stats SET level=?, "
                         "hp = hp + 20, atk = atk + 2, def = def + 1, "
                         "spd = spd + 1, mana = mana + 5 WHERE id=1", (level,))
        conn.execute("UPDATE stats SET xp=? WHERE id=1", (xp,))
        try:    # mission tracking: character level (high-water mark)
            conn.execute("UPDATE missions SET progress = MAX(progress, ?) "
                         "WHERE mtype='level' AND claimed=0", (level,))
        except sqlite3.OperationalError:
            pass    # missions table not created yet (legacy callers)
        conn.commit()
        return {"level": level, "xp": xp, "needed": xp_for_level(level),
                "levels_gained": levels_gained}


# -------------------------------------------------------------- resources

def get_resources():
    """Current HP/mana pools. Regenerates over time (a slice of max per
    minute), so coming back later always feels rewarded. The pools start
    full the first time they are read on a legacy database.
    """
    base = get_base_stats()                     # also creates the stats row
    max_hp, max_mana = base["hp"], base["mana"]
    with _connect() as conn:
        row = conn.execute("SELECT hp_current, mana_current, regen_at "
                           "FROM stats WHERE id=1").fetchone()
        if row is None:
            return {"hp": max_hp, "mana": max_mana}
        hp_current, mana_current, regen_at = row
        now = int(time.time())
        if hp_current is None or hp_current < 0 or mana_current is None \
                or mana_current < 0 or not regen_at:
            conn.execute("UPDATE stats SET hp_current=?, mana_current=?, regen_at=? "
                         "WHERE id=1", (max_hp, max_mana, now))
            conn.commit()
            return {"hp": max_hp, "mana": max_mana}
        elapsed = max(0, now - regen_at)
        if elapsed >= 60:
            minutes = elapsed / 60.0
            hp_current = int(min(max_hp, hp_current
                                 + max(1.0, max_hp * settings.HP_REGEN_PER_MIN) * minutes))
            mana_current = int(min(max_mana, mana_current
                                   + max(1.0, max_mana * settings.MANA_REGEN_PER_MIN) * minutes))
            conn.execute("UPDATE stats SET hp_current=?, mana_current=?, regen_at=? "
                         "WHERE id=1", (hp_current, mana_current, now))
            conn.commit()
        return {"hp": int(hp_current), "mana": int(mana_current)}


def adjust_resources(hp_delta=0, mana_delta=0):
    """Spend or restore HP/mana (positive = restore). Clamped to [0, max]."""
    res = get_resources()          # regenerates first, so nothing is wasted
    base = get_base_stats()
    hp = int(max(0, min(base["hp"], res["hp"] + hp_delta)))
    mana = int(max(0, min(base["mana"], res["mana"] + mana_delta)))
    with _connect() as conn:
        conn.execute("UPDATE stats SET hp_current=?, mana_current=? WHERE id=1",
                     (hp, mana))
        conn.commit()
    return {"hp": hp, "mana": mana}


# --------------------------------------------------------------- missions

def sync_missions():
    """Load data/missions.txt into the missions table.

    Definitions refresh on every start, but progress and claimed state
    are preserved for keys that already exist.
    """
    entries = content.parse_named(settings.DATA_DIR, "missions.txt")
    with _connect() as conn:
        for key, entry in entries.items():
            conn.execute("""INSERT INTO missions
                            (key, name, description, mtype, target,
                             reward_points, reward_xp, reward_artifact_points)
                            VALUES (?,?,?,?,?,?,?,?)
                            ON CONFLICT(key) DO UPDATE SET
                              name=excluded.name,
                              description=excluded.description,
                              mtype=excluded.mtype,
                              target=excluded.target,
                              reward_points=excluded.reward_points,
                              reward_xp=excluded.reward_xp,
                              reward_artifact_points=excluded.reward_artifact_points""",
                         (key,
                          content.as_str(entry, "name", key),
                          content.as_str(entry, "desc"),
                          content.as_str(entry, "type", "math_correct"),
                          content.as_int(entry, "target", 1),
                          content.as_int(entry, "reward_points", 0),
                          content.as_int(entry, "reward_xp", 0),
                          content.as_int(entry, "reward_artifact_points", 0)))
        conn.commit()


def get_missions():
    with _connect() as conn:
        return conn.execute("SELECT * FROM missions ORDER BY key").fetchall()


def bump_mission(mtype, amount=1):
    """Counter progress (math rounds solved, ...). Never decreases."""
    with _connect() as conn:
        conn.execute("UPDATE missions SET progress = progress + ? "
                     "WHERE mtype=? AND claimed=0", (amount, mtype))
        conn.commit()


def set_mission(mtype, value):
    """High-water-mark progress (character level, total upgrades, ...)."""
    with _connect() as conn:
        conn.execute("UPDATE missions SET progress = MAX(progress, ?) "
                     "WHERE mtype=? AND claimed=0", (value, mtype))
        conn.commit()


def claim_mission(key):
    """Claim the rewards of a completed mission. Returns (ok, message)."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM missions WHERE key=?", (key,)).fetchone()
        if row is None:
            return False, "Unknown mission"
        if row["claimed"]:
            return False, "Already claimed"
        if row["progress"] < row["target"]:
            return False, "Not complete yet"
        conn.execute("UPDATE missions SET claimed=1 WHERE key=?", (key,))
        if row["reward_points"]:
            conn.execute("UPDATE points SET points = points + ?, last_updated=?",
                         (row["reward_points"], int(time.time())))
        if row["reward_artifact_points"]:
            conn.execute("UPDATE points SET artifact_points = artifact_points + ?",
                         (row["reward_artifact_points"],))
        conn.commit()
    if row["reward_xp"]:
        add_xp(row["reward_xp"])
    return True, "Reward claimed!"


# ------------------------------------------------------------------- gear

def get_equipped_gear():
    with _connect() as conn:
        rows = conn.execute("SELECT slot, item_key FROM equipped_gear").fetchall()
    return {row["slot"]: row["item_key"] for row in rows}


def equip_gear(slot, item_key):
    """Equip an item into its gear slot (fails on slot mismatch)."""
    with _connect() as conn:
        item = conn.execute("SELECT slot FROM item_defs WHERE key=?",
                            (item_key,)).fetchone()
        if item is None or item["slot"] != slot:
            return False
        conn.execute("INSERT OR REPLACE INTO equipped_gear (slot, item_key) "
                     "VALUES (?, ?)", (slot, item_key))
        conn.commit()
    return True


def unequip_gear(slot):
    with _connect() as conn:
        conn.execute("DELETE FROM equipped_gear WHERE slot=?", (slot,))
        conn.commit()


# ---------------------------------------------------------------- skills

def _parse_upgrade_names(raw):
    """Tolerate both JSON and the old python-repr storage format."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        try:
            data = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return []
    names = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict) and "name" in item:
                names.append(item["name"])
            else:
                name = getattr(item, "name", None)
                if name:
                    names.append(name)
    return names


def load_skill_progress():
    """Return {skill_name: {"level": int, "upgrades": [upgrade names]}}."""
    progress = {}
    with _connect() as conn:
        rows = conn.execute("SELECT name, level, active_upgrades FROM skills").fetchall()
    for name, level, upgrades_raw in rows:
        progress[name] = {"level": level, "upgrades": _parse_upgrade_names(upgrades_raw)}
    return progress


def save_skill_progress(name, level, upgrade_names):
    payload = json.dumps(list(upgrade_names))
    with _connect() as conn:
        conn.execute(
            "UPDATE skills SET level = ?, active_upgrades = ?, unlocked_paths = ? WHERE name = ?",
            (level, payload, payload, name))
        try:    # mission tracking: total upgrades owned
            total = sum(len(_parse_upgrade_names(row[0])) for row in
                        conn.execute("SELECT active_upgrades FROM skills").fetchall())
            conn.execute("UPDATE missions SET progress = MAX(progress, ?) "
                         "WHERE mtype='upgrades' AND claimed=0", (total,))
        except sqlite3.OperationalError:
            pass    # missions table not created yet (legacy callers)
        conn.commit()


# ------------------------------------------------------------- equipped

def get_equipped_artifacts():
    with _connect() as conn:
        rows = conn.execute("SELECT slot, artifact_id FROM equipped ORDER BY slot").fetchall()
    return {slot: artifact_id for slot, artifact_id in rows}


def set_equipped_artifact(slot, artifact_id):
    with _connect() as conn:
        duplicate = conn.execute(
            "SELECT slot FROM equipped WHERE artifact_id=?", (artifact_id,)).fetchone()
        if duplicate and duplicate[0] != slot:
            return False
        conn.execute("UPDATE equipped SET artifact_id=? WHERE slot=?", (artifact_id, slot))
        conn.commit()
        return True


def remove_equipped_artifact(slot, artifact_id):
    with _connect() as conn:
        conn.execute("DELETE FROM equipped WHERE artifact_id=? AND slot=?", (artifact_id, slot))
        conn.commit()


# ----------------------------------------------------------- artifacts

def get_all_artifacts():
    with _connect() as conn:
        return conn.execute("SELECT * FROM artifacts").fetchall()


def get_artifact(artifact_id):
    with _connect() as conn:
        return conn.execute(
            "SELECT name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, "
            "sub_stat2, sub_stat2_value, level, exp, max_level, def_key "
            "FROM artifacts WHERE id=?", (artifact_id,)).fetchone()


def add_artifact(artifact):
    """Insert a generated artifact dict (see generate_artifact_by_level).

    Returns the new artifact's id.
    """
    with _connect() as conn:
        cursor = conn.execute(
            """INSERT INTO artifacts
               (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value,
                sub_stat2, sub_stat2_value, max_level, def_key)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (artifact["name"], artifact["main_stat"], artifact["main_stat_value"],
             artifact.get("sub_stat1"), artifact.get("sub_stat1_value"),
             artifact.get("sub_stat2"), artifact.get("sub_stat2_value"),
             artifact["max_level"], artifact["def_key"]))
        conn.commit()
        try:    # mission tracking: artifacts owned
            conn.execute("UPDATE missions SET progress = MAX(progress, "
                         "(SELECT COUNT(*) FROM artifacts)) "
                         "WHERE mtype='artifacts' AND claimed=0")
            conn.commit()
        except sqlite3.OperationalError:
            pass    # missions table not created yet (legacy callers)
        return cursor.lastrowid


def roll_stat(stat_name):
    low = random.choice([True, False])
    if "Crit Rate%" in stat_name:
        value = random.uniform(1.0, 2.0) if low else random.uniform(1.8, 3.0)
        return round(value / 100.0, 4)
    if "%" in stat_name:
        value = random.uniform(1.0, 3.5) if low else random.uniform(3.5, 7.5)
        return round(value / 100, 4)
    return random.randint(10, 40) if low else random.randint(30, 100)


def get_artifact_stat_total(artifact, stat_name):
    total = 0
    found = False
    for stat_col, value_col in ((2, 3), (4, 5), (6, 7)):
        if artifact[stat_col] == stat_name and artifact[value_col] is not None:
            total += artifact[value_col]
            found = True
    return total if found else None


def format_stat_value(stat_name, value):
    if value is None:
        return "-"
    if "%" in stat_name:
        return f"{value * 100:.1f}%"
    return f"{int(value)}"


def level_up_artifact(artifact_id, feed_exp):
    """Feed EXP into an artifact, leveling it up and improving stats.

    Returns a result dict, or None when the artifact is missing or maxed.
    """
    with _connect() as conn:
        c = conn.cursor()
        c.execute("""SELECT level, exp, main_stat, main_stat_value,
                            sub_stat1, sub_stat1_value,
                            sub_stat2, sub_stat2_value, max_level
                     FROM artifacts WHERE id=?""", (artifact_id,))
        artifact = c.fetchone()
        if not artifact:
            return None
        (level, exp, main_stat, main_stat_value,
         sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value, max_level) = artifact
        if level >= max_level:
            return None

        exp += feed_exp
        exp_required = 100 + (level * 20)
        levels_gained = 0
        stats_improved = {}
        initial = (main_stat_value, sub_stat1_value, sub_stat2_value)

        while exp >= exp_required and level < max_level:
            exp -= exp_required
            level += 1
            levels_gained += 1
            exp_required = 100 + (level * 20)
            main_stat_value += roll_stat(main_stat)
            if level % 4 == 0:
                candidates = [(s, v) for s, v in
                              ((sub_stat1, "sub1"), (sub_stat2, "sub2")) if s]
                if candidates:
                    _, chosen = random.choice(candidates)
                    if chosen == "sub1":
                        sub_stat1_value += roll_stat(sub_stat1)
                    else:
                        sub_stat2_value += roll_stat(sub_stat2)

        if main_stat_value > initial[0]:
            stats_improved["main"] = ("main", main_stat, initial[0], main_stat_value)
        if sub_stat1 and sub_stat1_value and sub_stat1_value > initial[1]:
            stats_improved["sub1"] = ("sub1", sub_stat1, initial[1], sub_stat1_value)
        if sub_stat2 and sub_stat2_value and sub_stat2_value > initial[2]:
            stats_improved["sub2"] = ("sub2", sub_stat2, initial[2], sub_stat2_value)

        c.execute("""UPDATE artifacts
                     SET level=?, exp=?, main_stat_value=?, sub_stat1_value=?, sub_stat2_value=?
                     WHERE id=?""",
                  (level, exp, main_stat_value, sub_stat1_value, sub_stat2_value, artifact_id))
        conn.commit()

    return {
        "levels_gained": levels_gained,
        "stats_improved": list(stats_improved.values()),
        "new_level": level,
        "exp": exp,
        "exp_required": exp_required,
    }


# ---------------------------------------------- artifact name generation

_FALLBACK_ADJECTIVES = [
    "Ancient", "Blazing", "Cursed", "Dreadful", "Ethereal", "Feral", "Gleaming",
    "Hollow", "Infernal", "Jagged", "Keen", "Luminous", "Molten", "Noble",
    "Ominous", "Prismatic", "Quiet", "Runic", "Sacred", "Turbo", "Vengeful",
    "Whispering", "Zealous",
]
_FALLBACK_ITEM_TYPES = [
    "Amulet", "Band", "Charm", "Crown", "Emblem", "Fang", "Grasp", "Helm",
    "Idol", "Locket", "Pendant", "Ring", "Sigil", "Talisman", "Vestige", "Wraps",
]


def _load_wordlist(filename, fallback):
    path = os.path.join(settings.WORDLISTS_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
        return words or fallback
    except OSError:
        return fallback


def generate_random_artifact_name():
    adjectives = _load_wordlist("adjectives.txt", _FALLBACK_ADJECTIVES)
    item_types = _load_wordlist("item_types.txt", _FALLBACK_ITEM_TYPES)
    adj = random.choice(adjectives)
    second_adj = random.choice(adjectives)
    item = random.choice(item_types)
    return random.choice([
        f"{adj} {second_adj} {item}",
        f"{item} of {adj} {second_adj}",
        f"{item} with {adj}",
        f"{item} of {adj}",
        f"{adj} {item} of {second_adj}",
    ])


def _roll_in_range(stat_name, low, high):
    value = random.uniform(low, high)
    if "%" in stat_name:
        return round(value, 4)
    return int(round(value))


def generate_artifact_by_level(level):
    """Generate an artifact instance from the archetypes in
    data/artifacts.txt (weighted pick, stats rolled within the defined
    ranges, icon/lore/rarity provided by the archetype).

    Higher reward levels add more sub stats. Returns a dict for
    add_artifact(), or None when no archetypes exist.
    """
    defs = get_artifact_defs()
    if not defs:
        return None
    weights = [max(1, d["weight"]) for d in defs]
    chosen = random.choices(list(defs), weights=weights, k=1)[0]
    main_pool = json.loads(chosen["main_stats"] or "{}")
    sub_pool = json.loads(chosen["sub_stats"] or "{}")
    if not main_pool:
        return None

    main_stat = random.choice(list(main_pool))
    low, high = main_pool[main_stat]
    artifact = {
        "def_key": chosen["key"],
        "name": generate_random_artifact_name(),
        "main_stat": main_stat,
        "main_stat_value": _roll_in_range(main_stat, low, high),
        "max_level": chosen["max_level"],
    }
    if level >= 2 and sub_pool:
        options = [s for s in sub_pool if s != main_stat] or list(sub_pool)
        sub1 = random.choice(options)
        low, high = sub_pool[sub1]
        artifact["sub_stat1"] = sub1
        artifact["sub_stat1_value"] = _roll_in_range(sub1, low, high)
    if level >= 8:
        options = [s for s in sub_pool
                   if s not in (main_stat, artifact.get("sub_stat1"))]
        if options:
            sub2 = random.choice(options)
            low, high = sub_pool[sub2]
            artifact["sub_stat2"] = sub2
            artifact["sub_stat2_value"] = _roll_in_range(sub2, low, high)
    return artifact


# ------------------------------------------------------- definitions sync

def sync_item_defs():
    """Load data/items.txt into item_defs.

    The text file is the source of truth: rows are rebuilt on every
    start, and inventory rows for removed definitions are cleaned up.
    """
    entries = content.parse_named(settings.DATA_DIR, "items.txt")
    with _connect() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM item_defs")
        for key, entry in entries.items():
            c.execute("""INSERT INTO item_defs
                         (key, name, type, category, rarity, slot, stats, price,
                          sell_price, shop, stock, stackable, max_stack,
                          icon, color, description)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (key,
                       content.as_str(entry, "name", key),
                       content.as_str(entry, "type", "misc"),
                       content.as_str(entry, "category", "normal"),
                       content.as_str(entry, "rarity", "common"),
                       content.as_str(entry, "slot") or None,
                       json.dumps(content.as_stat_map(entry, "stats")),
                       content.as_int(entry, "price", 0),
                       content.as_int(entry, "sell_price", 0),
                       1 if content.as_bool(entry, "shop", False) else 0,
                       content.as_int(entry, "stock", -1),
                       1 if content.as_bool(entry, "stackable", False) else 0,
                       content.as_int(entry, "max_stack", 1),
                       content.as_str(entry, "icon"),
                       content.as_str(entry, "color", "200,200,200"),
                       content.as_str(entry, "desc")))
        c.execute("DELETE FROM inventory WHERE item_key NOT IN (SELECT key FROM item_defs)")
        conn.commit()


def sync_artifact_defs():
    """Load data/artifacts.txt into artifact_defs (rebuilt every start)."""
    entries = content.parse_named(settings.DATA_DIR, "artifacts.txt")
    with _connect() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM artifact_defs")
        for key, entry in entries.items():
            c.execute("""INSERT INTO artifact_defs
                         (key, name, rarity, weight, icon, color, max_level,
                          main_stats, sub_stats, lore)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (key,
                       content.as_str(entry, "name", key),
                       content.as_str(entry, "rarity", "common"),
                       content.as_int(entry, "weight", 1),
                       content.as_str(entry, "icon", "gem"),
                       content.as_str(entry, "color", "200,200,200"),
                       content.as_int(entry, "max_level", 20),
                       json.dumps({k: list(v) for k, v in
                                   content.as_range_map(entry, "main_stats").items()}),
                       json.dumps({k: list(v) for k, v in
                                   content.as_range_map(entry, "sub_stats").items()}),
                       content.as_str(entry, "lore")))
        conn.commit()


def get_item_defs(shop_only=False):
    query = "SELECT * FROM item_defs"
    if shop_only:
        query += " WHERE shop = 1"
    query += " ORDER BY price, name"
    with _connect() as conn:
        return conn.execute(query).fetchall()


def get_item_def(item_key):
    with _connect() as conn:
        return conn.execute("SELECT * FROM item_defs WHERE key=?",
                            (item_key,)).fetchone()


def get_artifact_defs():
    with _connect() as conn:
        return conn.execute("SELECT * FROM artifact_defs").fetchall()


def get_artifact_def(def_key):
    with _connect() as conn:
        return conn.execute("SELECT * FROM artifact_defs WHERE key=?",
                            (def_key,)).fetchone()


def get_artifacts_by_ids(ids):
    """Load several artifact rows at once (used by the character page)."""
    if not ids:
        return []
    with _connect() as conn:
        placeholders = ",".join("?" * len(ids))
        return conn.execute(
            "SELECT id, name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, "
            f"sub_stat2, sub_stat2_value, def_key FROM artifacts WHERE id IN ({placeholders})",
            list(ids)).fetchall()


# ------------------------------------------------------- inventory / shop

def get_inventory_items():
    """Owned items: definition fields plus quantity."""
    with _connect() as conn:
        return conn.execute("""
            SELECT item_defs.*, inventory.quantity
            FROM inventory
            JOIN item_defs ON inventory.item_key = item_defs.key
            WHERE inventory.quantity > 0
            ORDER BY item_defs.type, item_defs.name""").fetchall()


def get_shop_items():
    """Shop stock straight from the defs (stock: -1 = unlimited)."""
    return get_item_defs(shop_only=True)


def _grant_item(conn, item_key, quantity=1):
    """Add to inventory inside an open transaction (stacking aware)."""
    item = conn.execute("SELECT stackable, max_stack FROM item_defs WHERE key=?",
                        (item_key,)).fetchone()
    if item is None:
        return False
    if item["stackable"]:
        conn.execute("""INSERT INTO inventory (item_key, quantity) VALUES (?, ?)
                        ON CONFLICT(item_key) DO UPDATE SET quantity = MIN(
                          (SELECT max_stack FROM item_defs
                           WHERE key = inventory.item_key),
                          inventory.quantity + excluded.quantity)""",
                     (item_key, quantity))
    else:
        conn.execute("INSERT OR IGNORE INTO inventory (item_key, quantity) VALUES (?, 1)",
                     (item_key,))
    return True


def add_item(item_key, quantity=1):
    """Grant an item (quest rewards, drops)."""
    with _connect() as conn:
        if not _grant_item(conn, item_key, quantity):
            return False
        conn.commit()
    return True


def purchase_item(item_key):
    """Atomically buy an item from the shop. Returns (success, message)."""
    with _connect() as conn:
        try:
            row = conn.execute("SELECT price, stock FROM item_defs "
                               "WHERE key=? AND shop=1", (item_key,)).fetchone()
            if row is None:
                return False, "Not for sale"
            if row["stock"] == 0:
                return False, "Sold out"
            points_row = conn.execute("SELECT points FROM points").fetchone()
            if (points_row["points"] if points_row else 0) < row["price"]:
                return False, "Not enough points"
            conn.execute("UPDATE points SET points = points - ?", (row["price"],))
            if row["stock"] > 0:
                conn.execute("UPDATE item_defs SET stock = stock - 1 WHERE key=?",
                             (item_key,))
            if not _grant_item(conn, item_key):
                conn.rollback()
                return False, "Unknown item"
            conn.commit()
            return True, "Purchase successful"
        except sqlite3.Error as error:
            conn.rollback()
            return False, str(error)


def _consume_item(item_key, quantity=1):
    """Remove quantity from the inventory stack (inside a transaction)."""
    with _connect() as conn:
        conn.execute("UPDATE inventory SET quantity = quantity - ? WHERE item_key=?",
                     (quantity, item_key))
        conn.execute("DELETE FROM inventory WHERE item_key=? AND quantity <= 0",
                     (item_key,))
        conn.commit()


def use_item(item_key, quantity=1):
    """Use a consumable. Its hp/mana stats restore the resource pools.

    Returns (success, message).
    """
    item = get_item_def(item_key)
    if item is None:
        return False, "Unknown item"
    if item["type"] != "consumable":
        return False, "That can't be used"
    with _connect() as conn:
        row = conn.execute("SELECT quantity FROM inventory WHERE item_key=?",
                           (item_key,)).fetchone()
    if row is None or row["quantity"] < quantity:
        return False, "You don't have that many"

    try:
        stats = json.loads(item["stats"] or "{}")
    except ValueError:
        stats = {}
    hp = float(stats.get("hp", 0))
    mana = float(stats.get("mana", 0))
    if hp or mana:
        adjust_resources(hp, mana)
        if hp and mana:
            message = f"Restored {int(hp)} HP and {int(mana)} mana"
        elif hp:
            message = f"Restored {int(hp)} HP"
        else:
            message = f"Restored {int(mana)} mana"
    else:
        message = "Nothing happened..."

    _consume_item(item_key, quantity)
    return True, message


def sell_item(item_key, quantity=1):
    """Sell an owned item back for its sell_price per unit.

    Equipped gear has to be taken off first. Returns (success, message).
    """
    item = get_item_def(item_key)
    if item is None:
        return False, "Unknown item"
    if item["sell_price"] <= 0:
        return False, "That can't be sold"
    if item["slot"] and item_key in get_equipped_gear().values():
        return False, "Unequip it first"
    with _connect() as conn:
        row = conn.execute("SELECT quantity FROM inventory WHERE item_key=?",
                           (item_key,)).fetchone()
        if row is None or row["quantity"] < quantity:
            return False, "You don't have that many"
        conn.execute("UPDATE inventory SET quantity = quantity - ? WHERE item_key=?",
                     (quantity, item_key))
        conn.execute("DELETE FROM inventory WHERE item_key=? AND quantity <= 0",
                     (item_key,))
        payout = item["sell_price"] * quantity
        conn.execute("UPDATE points SET points = points + ?, last_updated=?",
                     (payout, int(time.time())))
        conn.commit()
    return True, f"+{payout} points"



