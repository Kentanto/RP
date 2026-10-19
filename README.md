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

### Completing a mission (author only)
There is no "complete" button or checkbox in the UI — players cannot finish
missions themselves. To complete one for your users:
1. Open its JSON and set `"completed": true` (the hidden author mark), or move
   the file straight into `completed_missions/`.
2. Commit + push. Every player's app then automatically:
   - moves the file from `missions/` into `completed_missions/`,
   - adds the mission's XP to the player exactly once (tracked per player in `cache/credited_missions.json`),
   - handles level-ups and shows a "MISSION COMPLETED" notification.

To undo a completion, set `"completed": false` in its file under
`completed_missions/`. The app moves it back into `missions/` and removes the
XP recorded for that completion from the player's progress.

### Mission zoom
The MISSIONS tab has `- / % / + / RESET` zoom controls (60%–200%). The chosen
size is saved in each player's config and also scales the mission detail view.

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
  "completed": false
}
```
- `"xp"` is an integer XP amount; the `reward` value is display text only.
- `"completed"` is the hidden author mark. Players never see or set it in the
  UI; flip it to `true` (or move the file into `completed_missions/`) to finish
  the mission for everyone. A file moved directly into `completed_missions/`
  without a `"completed"` property still counts as completed. Setting the
  property to `false` there restores the mission to `missions/`.
