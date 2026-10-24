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
| `sounds/` | SFX files played by the central audio map (`athas/audio.py`), plus `songs/` for background music |
| `library/` | `item_types.txt` â€” the item types artifacts are generated from |
| `shop/` | Shop supply items as JSON files (git-synced, backed up); `_template.json` is a ready-to-edit starting point |
| `drops/` | Local hand-out files (gold, points, artifacts, notifications) â€” git-ignored, processed once, then deleted; `_template.json` is a ready-to-edit starting point |
| `backups/` | Local snapshots of the JSON data files (git-ignored) |

## Backups
On startup and every 30 minutes the app copies every `*.json` data file â€”
plus `cache/inventory.db` â€” into a new `backups/<date_time>/` folder,
mirroring each file's original folder structure (e.g.
`backups/2026-10-22_15-30-00/missions/<file>.json`). Every backup gets its
own folder, and folders older than 30 days are deleted automatically. The
`backups/` folder is git-ignored, so it is never committed or pushed.

## How the mission pipeline works
1. You work on mission files inside `draft_missions/` â€” they stay local.
2. When ready, move them into `missions/`.
3. The app commits and pushes the new mission after 30 seconds without another change.
4. Other users' apps pull on the configured interval â€” new files trigger a "New Mission Detected" notification.

Changes to `.json` or `.db` files in `cache/`, `missions/`, or
`completed_missions/` are automatically committed as `save file` and pushed
after 30 seconds without another change. The app pauses pulling while a local
save is waiting to commit or push.

### Completing a mission (author only)
There is no "complete" button or checkbox in the UI â€” players cannot finish
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
file whose content changed since it was credited counts as a fresh completion â€”
the old reward is revoked and the new one granted.

Git-ignored files (such as `cache/seen_missions.json`) are never committed or
pushed, and their changes never delay the autosave.

### Mission zoom
The MISSIONS tab has `- / % / + / RESET` zoom controls (60%â€“200%). The chosen
size is saved in each player's config and also scales the mission detail view.

### Skills
The dashboard's SKILLS button opens a skill catalogue separate from the
constellation ability tree. Every `*.json` file inside `skills/` is loaded â€”
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
edited â€” including changes arriving through git sync. Files that fail
validation, or repeat a skill id that an earlier file already defined, are
skipped with an orange warning shown on the skills page, so one bad file
never breaks the rest.

Each skill defines its own upgrade tree in `upgrades`. Every node has an
`id`, `title`, `description`, `x`/`y` position on the map, and `max_rank`;
optionally `parents` (a list of node ids that must be unlocked first â€” a
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
  Chestplate, Ring, ...) â€” the type also names the artifact and biases
  which stats it rolls
* a **rarity** â€” Common, Uncommon, Rare, Epic, Legendary, Mythic â€” which
  sets the power multiplier, how many stats are rolled, and the shop price

Artifacts have **no level** â€” all their power comes from the rarity and
the workshop's upgrade levels (+1/20 up to +20/20). Every roll, starting
or upgrade, is a **low, mid or high roll** (50% / 30% / 20% â€” edit
`ROLL_TIER_WEIGHTS` in `athas/artifact_generator.py`), and upgrade rolls
grow 5% stronger for every upgrade level already on the artifact, so
late upgrades land noticeably harder.

Rolled stats come in four kinds:
* **main stats** (health, magic, attack, defense, speed) â€” granted directly
* **crit stats** (crit chance, crit damage) â€” granted directly
* **point-worth stats** (`worth_attack`, ...) â€” the bonus is added straight
  onto that stat's per-point DG rating on the DETAILED STATS page, and the
  level multiplier then scales the whole thing: 1 point = (60 + bonus) DG,
  then × 1.05 per level past the first (a worth bonus of 5 makes a point
  worth 65 DG at level 1, 65 x 1.05 at level 2, ...). Two artifacts raising
  different stats' worth can make very different builds out of the same point
  budget. Worth rolls are small and flat (+1/+2/+3) because the bonus sits
  on top of every single allocated point.
* **temp points** â€” extra allocatable temporary points granted while the
  artifact is equipped.

Rarity decides how many *different* stats sit on one artifact (Common 1 â€¦
Mythic 5); special stats roll with a lower weight than plain ones.

**Equipment** â€” artifacts must be **equipped** for their stats to apply,
and there are only **5 equipment slots**. The loadout lives in the player
config (`player.equipped_artifacts`) and shows as a clickable slot bar at
the top of the inventory ARTIFACTS tab (click a filled slot to unequip).
Unequipped gear gives nothing, and artifacts that leave the inventory
(forged away or revoked by an un-completed mission) leave their slot too.

**Workshop** â€” open any artifact to work on it (all prices are gold, all
rolls are random):
* **UPGRADE** â€” a low, mid or high roll into a random stat on the artifact,
  up to **+20** (baseline; edit `MAX_UPGRADE_LEVEL`). The price grows with
  the rarity and the current upgrade level.
* **DOWNGRADE** â€” takes the last upgrade back off and refunds half its gold.
* **REROLL STATS** â€” completely new random stat types with random starting
  numbers. Upgrades reset.
* **REROLL VALUES** â€” keeps the current stat types but re-rolls where the
  numbers went (like the artifact reroll in Genshin). Deliberately
  expensive, and the gold is never recoverable. The upgrade level stays:
  every upgrade is applied again from scratch, each with a fresh
  low/mid/high roll, so a reroll is a new chance at better numbers.

Artifacts don't use pictures â€” their cards show the rolled stat lines
directly. Hand-made JSON items in `items/` keep their images. Clicking a
card opens a detail view: a centered, rarity-lit card with description,
lore, the bonus list, the full upgrade history, and the workshop buttons.

There are only two ways to obtain artifacts:
1. **Mission rewards** â€” add `"artifact_reward": <count>` to a mission JSON.
   The rarity is rolled from the mission difficulty's loot table (E-rank
   missions drop Commonâ€“Rare, S-rank drop Epicâ€“Mythic) unless you pin it
   with `"artifact_rarity": "Rare"`.
2. **The Shop** â€” the PACKAGE: 10 random common artifacts for 400 gold.

The shop's shelves no longer sell random artifacts â€” they carry a fixed
supply catalogue instead, defined by the JSON files in `shop/` (one file
per supply; a file may also hold a list or `{"items": [...]}`, and names
starting with `_` â€” like `_template.json` â€” are never stocked). The
shipped catalogue: Bandage (50), Field Ration (80), Antidote (150),
Smoke Bomb (250), Mana Draught (400), Medkit (800), Elixir of Vigor
(1500), and a Healing Potion (5000) â€” a rare miracle medicine, hence the
price. The folder is git-synced and backed up like the other content
folders, so curating it locally and committing it updates the shop for
everyone; the built-in list is the fallback when the folder is empty.
Supplies are always in stock (no restock), and buying adds to the
player's stash, which lives in the database (so it syncs and persists) and
shows on the inventory SUPPLIES tab with the owned counts. Opening a
supply shows what it does and offers a USE button that spends one.

**Sacrifice / Forge** â€” on the inventory ARTIFACTS tab, press SACRIFICE and
select 3 artifacts of the same rarity, then FORGE consumes them and creates
1 artifact of the next rarity with fresh random stats (Mythic cannot be
fused â€” there is nothing higher).

**Detailed stats** â€” the DASHBOARD's DETAILED STATS button opens a page
that turns every regular stat into a simple, linear DG power rating â€” no
real-world units. Each stat awards DG per point (60 for every stat right
now; edit `STAT_DG_PER_POINT` in `athas/detailed_stats.py` to scale stats
differently), scaled by a compounding level multiplier: x1.05 for every
level past the first (1.05^(level-1)), so a level-12 hero measures
everything at x1.71. **Only equipped artifacts** add their bonuses, and
equipped point-worth artifacts add their bonus onto the per-point DG
rating before the level multiplier (a worth bonus of N makes every point
worth 60 + N DG, then scaled by the level multiplier). The page also
shows the two
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
points, generated artifacts, or a message â€” the app scans the folder
every 2 seconds, applies the grants, and **deletes the file**. A reward
popup confirms what was granted; its OK button stays disabled for the
first **2 seconds** so a popup that appears suddenly cannot be clicked
away by accident.

The folder always contains `_template.json` â€” a ready-to-edit template
with every supported key sitting at `0`. Copy it, rename the copy (the
new name must **not** start with an underscore â€” files that do are never
processed), fill in the values, save, and the app grants it once.

The folder is git-ignored, outside every git-sync path, and never backed
up â€” the app can never upload from it. Sharing a drop file with someone
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
  "artifact_reward": 1,
  "artifact_rarity": "Rare",
  "message": "Well done, Wanderer.",
  "notification": { "title": "System Message", "message": "Well done." }
}
```
`artifact_reward` grants that many generated artifacts;
`artifact_rarity` optionally pins their rarity. `message`
(or `msg` / `text`) shows as plain System text.
TXT format â€” one `key: value` pair per line (`key = value` works too,
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

## Audio (SFX map)
Every sound effect goes through `athas/audio.py`: an event name maps to
a wav file in `sounds/`, and unmapped or missing files stay silent.
The `audio` settings section controls it â€” `enabled` mutes everything,
`volume` is the background music and `sfx_volume` the effects.

Currently mapped events: `click`, `hover` and `back` (UI), `upgrade`,
`upgrade_max`, `equip`, `refund`, `reroll` and `forge` (workshop),
`buy` (shop), `level_up`, `mission_complete`, `reward` (progression
and drops) and `skill_unlock` (skill tree). To wire a new sound, drop
the wav into `sounds/` and add it to `EVENT_SOUNDS`.

random ideas:

(none right now â€” the previous five ideas were implemented: tiered
artifact rolls, upgrade-only artifacts, the JSON shop folder,
level-scaling point-worth bonuses, and the SFX map above.)
