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
| `drops/` | Local hand-out files (gold, points, notifications) — git-ignored, processed once, then deleted |
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

Rolled stats come in four kinds:
* **main stats** (health, magic, attack, defense, speed) — granted directly
* **crit stats** (crit chance, crit damage) — granted directly
* **point-worth stats** (`worth_attack`, ...) — every point allocated into
  that stat is worth extra DG on the DETAILED STATS page (the base is 60
  DG per point). Two artifacts raising different stats' worth can make
  very different builds out of the same point budget.
* **temp points** — extra allocatable temporary points granted while the
  artifact is equipped.

Rarity decides how many *different* stats sit on one artifact (Common 1 …
Mythic 5); special stats roll with a lower weight than plain ones.

**Equipment** — artifacts must be **equipped** for their stats to apply,
and there are only **5 equipment slots**. The loadout lives in the player
config (`player.equipped_artifacts`) and shows as a clickable slot bar at
the top of the inventory ARTIFACTS tab (click a filled slot to unequip).
Unequipped gear gives nothing, and artifacts that leave the inventory
(forged away or revoked by an un-completed mission) leave their slot too.

**Workshop** — open any artifact to work on it (all prices are gold, all
rolls are random):
* **UPGRADE** — a low or high roll into a random stat on the artifact,
  up to **+20** (baseline; edit `MAX_UPGRADE_LEVEL`). The price grows with
  the rarity and the current upgrade level.
* **DOWNGRADE** — takes the last upgrade back off and refunds half its gold.
* **REROLL STATS** — completely new random stat types with random starting
  numbers. Upgrades reset.
* **REROLL VALUES** — keeps the current stat types but re-rolls where the
  numbers went (like the artifact reroll in Genshin). Deliberately
  expensive, and the gold is never recoverable. Upgrades reset.

Artifacts don't use pictures — their cards show the rolled stat lines
directly. Hand-made JSON items in `items/` keep their images.

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
that turns every regular stat into a simple, linear DG power rating — no
real-world units. Each stat awards DG per point (60 for every stat right
now; edit `STAT_DG_PER_POINT` in `athas/detailed_stats.py` to scale stats
differently), scaled by a compounding level multiplier: x1.10 for every
level past the first (1.10^(level-1)), so a level-12 hero measures
everything at x2.85. **Only equipped artifacts** add their bonuses, and
equipped point-worth artifacts raise the per-point DG rating itself. The
page also shows the two
crit stats, derived from the stat totals (crit chance: 3% + Speed x 0.45%,
crit damage: 50% + Attack x 1.50%) with direct artifact crit rolls stacked
on top. Crit chance caps at 75% and crit damage at 300%. Below the crit
cards, a TOTAL DG card sums every stat's rating into one overall number,
with each stat's contribution listed in its own color and its own
capability description.
Below each stat, a capability reference compares the current DG rating
with a short description. Edit `STAT_CAPABILITY_RANGES` in
`athas/detailed_stats.py` to change the descriptions or add value bands; each
band uses a lower-inclusive and upper-exclusive DG range, and the final
band can use `None` as its open-ended upper bound.

Gold comes from mission `"gold"` rewards and is shown in the sidebar. The
`library/` folder is part of git sync, so curating `item_types.txt` locally
and committing it updates the loot pool for everyone.

## Drops folder
Drop a `*.json` or `*.txt` file into `drops/` to hand the local player
gold, xp, skill points, constellation points, temp points, permanent
points, or a notification — the app scans the folder every 2 seconds,
applies the grants, and **deletes the file**. A reward popup confirms
what was granted; its OK button stays disabled for the first **2 seconds**
so a popup that appears suddenly cannot be clicked away by accident.

The folder is git-ignored, outside every git-sync path, and never backed
up — the app can never upload from it. Sharing a drop file with someone
happens manually from the IDE, nothing else.

JSON format (any subset of the keys):
```json
{
  "gold": 100,
  "xp": 50,
  "skill_points": 1,
  "constellation_points": 2,
  "temp_points": 3,
  "perm_points": 1,
  "notification": { "title": "System Message", "message": "Well done." }
}
```
TXT format — one `key: value` pair per line (`key = value` works too,
spacing and case are free, and friendly aliases like `con points`,
`exp`, `money`, or `points` are accepted):
```
gold: 100
skill points: 1
notification: The System acknowledges your progress.
```

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

Random ideas:
- the drops folder should have a ready json file in there that isnt processed by default, so i can write any given reward be it gold, con points, skill points or even artifacts is supported, they are all in the ignored json file by default at 0 so i can change it copy the file and rename it, it should also support text so i can write messages

- instead of random artifacts in the store, keep the 10 packaged deal but replace the random ones with instead regular shop items such as bandages, medkits, healing potion in rising price, healing potion being significantly higher, like 5k gold. think of other supplies too i guess 

- the detailed view of artifacts by clicking on them is a little bad, could you make the interface look better still adhering to the systems look

- drops messages has no background when it processes something that wasnt supported,

- rerolling artifact values doesnt reset the artifact to level 0, but since each upgrade has a chance to hit a high or low number to add to it, it does that again for all levels with a new chance to get a higher number, the 