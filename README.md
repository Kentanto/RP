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
| `library/` | Word/name libraries used to generate artifacts |

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
recorded XP and unspent point rewards from the player's balances.

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
can only be unlocked once at least one of its parents has a rank. Ranks are
saved per player under the `player.skill_upgrades` key in the config.
Player skill points are a separate balance awarded by mission
`skill_points` rewards. The constellation tree stores its ranks separately
under the `constellations` key in player config. Existing constellation
ranks saved under the old `skills` key are migrated automatically. The
skills folder is included in git sync and autosave when sync is enabled.

## Mission file format
JSON files (`*.json`) inside `missions/`:
```json
{
  "title": "Mission Name Here",
  "description": "What needs to be done.",
  "story": "Longer flavour text shown in the mission detail view.",
  "difficulty": "C",
  "reward": "Bronze Key",
  "xp": 100,
   "constellation_points": 0,
   "skill_points": 0,
  "completed": false
}
```
- `"xp"`, `"constellation_points"`, and `"skill_points"` are hidden integer
   amounts granted when the mission completes. They may be omitted or set to
   `0`. Skill points add to the skill-upgrade balance.
- `"reward"` is display text only; it is shown to the player without revealing
   the numeric reward fields.
- `"completed"` is the hidden author mark. Players never see or set it in the
   UI; flip it to `true` (or move the file into `completed_missions/`) to finish
   the mission for everyone. A file moved directly into `completed_missions/`
   without a `"completed"` property still counts as completed. Setting the
   property to `false` there restores the mission to `missions/`.
