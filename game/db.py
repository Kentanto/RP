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

    sync_item_defs()
    sync_artifact_defs()



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


def get_artifact_defs():
    with _connect() as conn:
        return conn.execute("SELECT * FROM artifact_defs").fetchall()


def get_artifact_def(def_key):
    with _connect() as conn:
        return conn.execute("SELECT * FROM artifact_defs WHERE key=?",
                            (def_key,)).fetchone()


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



