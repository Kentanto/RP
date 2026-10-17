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
| `draft_missions/` | Hidden WIP missions (gitignored) |
| `cache/` | Cached seen files (gitignored) |
| `icons/` | `background_menu.png` used as fullscreen background |
| `sounds/` | SFX files reserved for future use |
| `library/` | Word/name libraries used to generate artifacts |

## How the mission pipeline works
1. You work on mission files inside `draft_missions/` — they stay local.
2. When ready, move them into `missions/`.
3. Commit + push to git.
4. The app auto-pulls on the configured interval — new files trigger a "New Mission Detected" notification.
5. Other users running the app will pull and see the same missions.

## Mission file format
JSON files (`*.json`) inside `missions/`:
```json
{
  "title": "Mission Name Here",
  "description": "What needs to be done.",
  "story": "Longer flavour text shown in the mission detail view.",
  "difficulty": "C",
  "reward": "Bronze Key, +100 EXP",
  "completed": false
}
```
