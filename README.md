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

## Tests

Headless smoke tests:

    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tests/smoke_test.py