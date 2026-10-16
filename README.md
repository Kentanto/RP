# Athas

A text & UI game featuring stats, artifacts, a skill tree and small minigames.

## The game loop

* **Math Arena** — pay an entry fee per tier (harder tiers unlock at
  character levels 8/15/25), solve equations, and earn skill points,
  artifact points, XP and artifact drops. Consecutive correct answers
  build a streak that boosts artifact point rewards; leaving mid-round
  refunds the fee.
* **Missions** — objectives that track themselves (rounds solved,
  artifacts owned, level, upgrades unlocked). Press Claim to collect
  the rewards. Edit `data/missions.txt` to add or retune them.
* **Inventory** — click any item for its actions: consumables restore
  HP/mana, gear equips straight from the bag, and anything with a sell
  price can be sold back for points.
* **Resources** — HP and mana are live pools: they regenerate over
  time (also while the game is closed) and potions restore them
  instantly.

## Run it

The easiest way is the launcher. If `launcher.py` sits somewhere alone it
creates an `Athas/` folder, clones the project into it, and puts itself
there. Every rerun afterwards pulls the latest changes with git, restores
missing files, prepares a `.venv` (installs pygame) and starts the game
from source:

    python launcher.py

You can also run the game directly:

    python -m pip install -r requirements.txt
    python athas.py

## Adding content (no code required)

All game content lives in plain text files inside `data/`, each with a
comment legend at the top:

* `data/items.txt` — items and weapons (type, rarity, stats, price, shop
  stock, icon shape + color, and the `special` category). Equippable
  gear declares a `slot:` (weapon/head/chest/trinket) and feeds the
  character stats page. To add a sword, copy a `[key]` block, edit, done.
* `data/artifacts.txt` — artifact archetypes. The artifact system is
  self-generating: it picks an archetype, rolls stats within your ranges,
  and draws its icon from the shape and color you set.
* `data/abilities.txt` — the ability tree (roots, upgrades, costs,
  requirements, glyphs). Node positions are computed automatically.
* `data/missions.txt` — missions: an objective `type`
  (math_correct/artifacts/level/upgrades), a `target`, and the rewards
  paid out on claim. Progress is tracked automatically.

The game syncs these files into its database on every start; run
`python init_items.py` to check them without launching.

## Tests

Headless smoke tests:

    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tests/smoke_test.py