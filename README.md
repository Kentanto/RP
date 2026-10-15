# Athas

A text & UI game featuring stats, artifacts, a skill tree and small minigames.

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

The game syncs these files into its database on every start; run
`python init_items.py` to check them without launching.

## Tests

Headless smoke tests:

    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tests/smoke_test.py