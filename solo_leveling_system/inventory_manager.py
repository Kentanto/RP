"""
Inventory Manager -- handles two categories:
  * Items     : hand-made JSON files in items/*.json  (scanned, git-synced)
  * Artifacts : auto-generated from librarby/*.txt, stored in SQLite
"""
import json
import random
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class InventoryItem:
    uid: str
    name: str
    category: str          # "item" | "artifact"
    item_type: str
    description: str
    story: str
    rarity: str            # Common, Uncommon, Rare, Epic, Legendary, Mythic
    image_path: str        # absolute or relative to rp root
    stats: Dict[str, Any]
    count: int = 1
    level: int = 1
    source_file: str = ""  # for JSON items


class InventoryManager:
    RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"]
    TIER_WEIGHTS = [40, 25, 15, 10, 7, 3]

    def __init__(
        self,
        items_dir: str,
        librarby_dir: str,
        cache_dir: str,
        rp_root: str,
    ):
        self.items_dir = Path(items_dir)
        self.librarby_dir = Path(librarby_dir)
        self.cache_dir = Path(cache_dir)
        self.rp_root = Path(rp_root)

        self.items_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / "inventory.db"
        self._init_db()
        self._ensure_seed_artifacts(count=20)

    # --- Database ---
    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    item_type   TEXT NOT NULL,
                    adjective   TEXT NOT NULL,
                    rarity      TEXT NOT NULL,
                    level       INTEGER DEFAULT 1,
                    stats       TEXT DEFAULT '{}',
                    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _read_wordlist(self, filename: str) -> List[str]:
        path = self.librarby_dir / filename
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8")
        return [ln.strip() for ln in raw.splitlines() if ln.strip()]

    # --- Generation ---
    def _generate_random_artifact(self) -> Dict[str, Any]:
        adj = random.choice(self._read_wordlist("adjectives.txt") or ["Unknown"])
        nome = random.choice(self._read_wordlist("Artifact_names.txt") or ["Relic"])
        itype = random.choice(self._read_wordlist("item_types.txt") or ["Artifact"])
        rarity = random.choices(self.RARITIES, weights=self.TIER_WEIGHTS)[0]
        return {
            "name": f"{adj} {nome}",
            "item_type": itype,
            "adjective": adj,
            "rarity": rarity,
            "level": 1,
            "stats": json.dumps(self._roll_stats(rarity)),
        }

    def _roll_stats(self, rarity: str) -> Dict[str, int]:
        base = {"attack": 0, "defense": 0, "magic": 0, "speed": 0, "health": 0}
        mult = {"Common": 1, "Uncommon": 2, "Rare": 4, "Epic": 7, "Legendary": 12, "Mythic": 20}.get(rarity, 1)
        for k in base:
            base[k] = random.randint(1, 5) * mult + random.randint(0, mult)
        return base

    def _ensure_seed_artifacts(self, count: int = 20):
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM artifacts")
            if cur.fetchone()[0] >= count:
                return
            for _ in range(count):
                a = self._generate_random_artifact()
                conn.execute("""
                    INSERT INTO artifacts (name, item_type, adjective, rarity, level, stats)
                    VALUES (:name, :item_type, :adjective, :rarity, :level, :stats)
                """, a)
            conn.commit()

    # --- Items (JSON scan) ---
    def scan_items(self) -> List[InventoryItem]:
        self.items_dir.mkdir(parents=True, exist_ok=True)
        items: List[InventoryItem] = []
        for file_path in self.items_dir.iterdir():
            if not file_path.is_file() or file_path.suffix.lower() != ".json":
                continue
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            img = data.get("image", "")
            img_path = self._resolve_image(img, file_path.parent)
            items.append(InventoryItem(
                uid=f"item:{file_path.stem}",
                name=data.get("name", file_path.stem.replace("_", " ").title()),
                category="item",
                item_type=data.get("type", "Misc"),
                description=data.get("description", ""),
                story=data.get("story", ""),
                rarity=data.get("rarity", "Common"),
                image_path=img_path,
                stats=data.get("stats", {}),
                count=data.get("count", 1),
                level=data.get("level", 1),
                source_file=str(file_path),
            ))
        return items

    def _resolve_image(self, img: str, fallback_dir: Path) -> str:
        if not img:
            return ""
        p = Path(img)
        if p.is_absolute() and p.exists():
            return str(p)
        cand = fallback_dir / img
        if cand.exists():
            return str(cand)
        cand2 = self.rp_root / "icons" / img
        if cand2.exists():
            return str(cand2)
        return str(cand)

    # --- Artifacts (DB read) ---
    def get_artifacts(self) -> List[InventoryItem]:
        items: List[InventoryItem] = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute("SELECT * FROM artifacts ORDER BY rarity DESC, level DESC"):
                stats = {}
                try:
                    stats = json.loads(row["stats"])
                except Exception:
                    pass
                items.append(InventoryItem(
                    uid=f"artifact:{row['id']}",
                    name=row["name"],
                    category="artifact",
                    item_type=row["item_type"],
                    description=f"{row['adjective']} artifact of unknown origin.",
                    story="This artifact was born from the chaotic mana of the dungeons.",
                    rarity=row["rarity"],
                    image_path="",
                    stats=stats,
                    count=1,
                    level=row["level"],
                    source_file=str(self.db_path),
                ))
        return items

    def all_inventory(self) -> List[InventoryItem]:
        return self.scan_items() + self.get_artifacts()

    # --- Admin ---
    def regenerate_artifacts(self, count: int = 20):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM artifacts")
            for _ in range(count):
                a = self._generate_random_artifact()
                conn.execute("""
                    INSERT INTO artifacts (name, item_type, adjective, rarity, level, stats)
                    VALUES (:name, :item_type, :adjective, :rarity, :level, :stats)
                """, a)
            conn.commit()

    def delete_artifact(self, uid: str):
        if not uid.startswith("artifact:"):
            return
        pk = uid.split(":", 1)[1]
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM artifacts WHERE id = ?", (pk,))
            conn.commit()
