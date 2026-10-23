# Athas

A PySide6-powered "System" style UI.

## Run
```bash
python main.py
```

## Folders
| Folder | Purpose |
|--------|---------|
| `missions/` | Active missions tracked by git (shareable) |
| `completed_missions/` | Missions retired after completion; setting `"completed": false` restores one |
| `draft_missions/` | Hidden WIP missions (gitignored) |
| `cache/` | Player cache and inventory database (synced by git) |
| `skills/` | Authored skill definitions stored as JSON |
| `icons/` | `background_menu.png` used as fullscreen background |
| `sounds/` | SFX files reserved for future use |
| `library/` | `item_types.txt` — the item types artifacts are generated from |
| `backups/` | Local snapshots of the JSON data files (git-ignored) |

## Backups
On startup and every 30 minutes the app copies every `*.json` data file —
plus `cache/inventory.db` — into a new `backups/<date_time>/` folder,
mirroring each file's original folder structure (e.g.
`backups/2026-10-22_15-30-00/missions/<file>.json`). Every backup gets its
own folder, and folders older than 30 days are deleted automatically. The
`backups/` folder is git-ignored, so it is never committed or pushed.

## How the mission pipeline works
1. You work on mission files inside `draft_missions/` — they stay local.
2. When ready, move them into `missions/`.
3. The app commits and pushes the new mission after 30 seconds without another change.
4. Other users' apps pull on the configured interval — new files trigger a "New Mission Detected" notification.

Changes to `.json` or `.db` files in `cache/`, `missions/`, or
`completed_missions/` are automatically committed as `save file` and pushed
after 30 seconds without another change. The app pauses pulling while a local
save is waiting to commit or push.

### Completing a mission (author only)
There is no "complete" button or checkbox in the UI — players cannot finish
missions themselves. To complete one for your users:
1. Open its JSON and set `"completed": true` (the hidden author mark), or move
   the file straight into `completed_missions/`.
2. The app commits and pushes the change after 30 seconds without another edit.
   Every player's app then automatically:
   - moves the file from `missions/` into `completed_missions/`,
   - adds its numeric rewards exactly once (tracked in `cache/credited_missions.json`),
   - handles level-ups and shows a "MISSION COMPLETED" notification.

To undo a completion, set `"completed": false` in its file under
`completed_missions/`. The app moves it back into `missions/` and removes the
recorded XP and unspent point rewards from the player's balances. The same
revocation happens when a credited mission file leaves the completed state any
other way (moved back into `missions/`, reworked, or deleted), and a completed
file whose content changed since it was credited counts as a fresh completion —
the old reward is revoked and the new one granted.

Git-ignored files (such as `cache/seen_missions.json`) are never committed or
pushed, and their changes never delay the autosave.

### Mission zoom
The MISSIONS tab has `- / % / + / RESET` zoom controls (60%–200%). The chosen
size is saved in each player's config and also scales the mission detail view.

### Skills
The dashboard's SKILLS button opens a skill catalogue separate from the
constellation ability tree. Every `*.json` file inside `skills/` is loaded —
one skill per file is the simplest format:
```json
{
  "id": "quick-strike",
  "title": "Quick Strike",
  "description": "A swift attack.",
  "image": "images/quick-strike.svg",
  "mana_cost": 8,
  "upgrade_cost": 1,
  "base_damage": 20,
  "upgrades": [
    {
      "id": "mastery",
      "title": "Quick Strike Mastery",
      "description": "Each rank makes the strike faster and sharper.",
      "x": 120, "y": 300,
      "max_rank": 5
    },
    {
      "id": "flowing-blade",
      "title": "Flowing Blade",
      "description": "Chain the strike into a second cut.",
      "x": 340, "y": 180,
      "max_rank": 2,
      "parents": ["mastery"],
      "color": "#ff9800"
    }
  ]
}
```
A file may also hold a plain list of skills or the wrapped
`{"skills": [...]}` format (like `skills/skills.json`). Files are read in
alphabetical order, and image paths are relative to the `skills/` folder.
The app reads these definitions through `SkillManager.load_skills()`; the
catalogue reloads automatically whenever a skill file is added, removed, or
edited — including changes arriving through git sync. Files that fail
validation, or repeat a skill id that an earlier file already defined, are
skipped with an orange warning shown on the skills page, so one bad file
never breaks the rest.

Each skill defines its own upgrade tree in `upgrades`. Every node has an
`id`, `title`, `description`, `x`/`y` position on the map, and `max_rank`;
optionally `parents` (a list of node ids that must be unlocked first — a
node without parents is a tree root) and a `color`. Node ids must be unique
within the skill, parents must exist in the same tree, and parent chains may
not form a cycle.

Skill cards show only the title, description, mana cost, and base damage.
Clicking a card opens that skill's upgrade tree in its own window, which
works exactly like the constellation map: drag to pan, scroll to zoom, and
click a node to spend `upgrade_cost` skill points and raise its rank. A node
can only be unlocked once at least one of its parents has a rank. Each
upgrade's rank is stored as a `rank` field on that upgrade inside the
skill's own JSON file, so progress lives with the skill itself. Ranks
previously saved under `player.skill_upgrades` in the config are migrated
into the skill files automatically. Player skill points are a separate
balance awarded by mission `skill_points` rewards. The constellation tree
stores its ranks separately under the `constellations` key in player
config. Existing constellation ranks saved under the old `skills` key are
migrated automatically. The skills folder is included in git sync and
autosave when sync is enabled.

## Artifacts & the Shop
Artifacts are auto-generated gear (weapons, armor, accessories) stored in
`cache/inventory.db`. Every artifact rolls:
* an **item type** from `library/item_types.txt` (Sword, Shield,
  Chestplate, Ring, ...) — the type also names the artifact and biases
  which stats it rolls
* a **rarity** — Common, Uncommon, Rare, Epic, Legendary, Mythic — which
  sets the power multiplier, how many stats are rolled, and the shop price
* a **level** that scales the rolled stats (mission rewards roll at the
  player's current level)

Rolled stats are either **main stats** (health, magic, attack, defense,
speed) or **crit stats** (crit chance, crit damage) granted directly.

There are only two ways to obtain artifacts:
1. **Mission rewards** — add `"artifact_reward": <count>` to a mission JSON.
   The rarity is rolled from the mission difficulty's loot table (E-rank
   missions drop Common–Rare, S-rank drop Epic–Mythic) unless you pin it
   with `"artifact_rarity": "Rare"`.
2. **The Shop** — the SHOP tab sells 6 generated artifacts for gold, plus a
   fixed **PACKAGE: 10 common artifacts for 400 gold**. Shelf stock is
   almost always Common, sometimes Uncommon, rarely Rare — anything higher
   must be earned or fused. The stock lives in the database (so it syncs
   and persists), RESTOCK rerolls it, and buying moves the artifact into
   the inventory with its origin recorded.

**Sacrifice / Forge** — on the inventory ARTIFACTS tab, press SACRIFICE and
select 3 artifacts of the same rarity, then FORGE consumes them and creates
1 artifact of the next rarity with fresh random stats (Mythic cannot be
fused — there is nothing higher).

**Detailed stats** — the DASHBOARD's DETAILED STATS button opens a page
that turns every regular stat into a physical measurement. Each stat has a
per-point unit — 1 ATK = 100 J of kinetic energy per strike, 1 DEF = 200 N
of impact force deflected per block, 1 SPD = 0.5 m/s of movement speed,
1 HP = 0.25 kJ of punishment absorbed before collapse, 1 MAG = 50 W of
arcane power channelled — and the measurement scales with a compounding
level multiplier: x1.05 for every level past the first (1.05^(level-1)), so
a level-12 hero measures everything at x1.71. The page also shows the two
crit stats, derived from the stat totals (crit chance: 3% + Speed x 0.45%,
crit damage: 50% + Attack x 1.50%) with direct artifact crit rolls stacked
on top. Crit chance caps at 75% and crit damage at 300%.

Gold comes from mission `"gold"` rewards and is shown in the sidebar. The
`library/` folder is part of git sync, so curating `item_types.txt` locally
and committing it updates the loot pool for everyone.

## Mission file format
JSON files (`*.json`) inside `missions/`:
```json
{
  "title": "Mission Name Here",
  "description": "What needs to be done.",
  "story": "Longer flavour text shown in the mission detail view.",
  "difficulty": "C",
  "reward": "Bronze Key, +100 Gold, 1 Artifact",
  "xp": 100,
  "gold": 100,
  "artifact_reward": 1,
  "artifact_rarity": "Rare",
   "constellation_points": 0,
   "skill_points": 0,
  "completed": false
}
```
- `"xp"`, `"constellation_points"`, `"skill_points"`, and `"gold"` are hidden integer
   amounts granted when the mission completes. They may be omitted or set to
   `0`. Skill points add to the skill-upgrade balance; gold is
   spent in the shop.
- `"artifact_reward"` grants that many generated artifacts when the mission
   completes. `"artifact_rarity"` optionally pins their rarity; otherwise it
   is rolled from the difficulty loot table. Un-completing a mission revokes
   its gold and removes the artifacts it granted.
- `"reward"` is display text only; it is shown to the player without revealing
   the numeric reward fields.
- `"completed"` is the hidden author mark. Players never see or set it in the
   UI; flip it to `true` (or move the file into `completed_missions/`) to finish
   the mission for everyone. A file moved directly into `completed_missions/`
   without a `"completed"` property still counts as completed. Setting the
   property to `false` there restores the mission to `missions/`.
