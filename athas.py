"""Athas — game entry point.

The implementation now lives in the `game` package; this file stays as the
launch target so existing workflows (and builds) keep working.
"""
from game.settings import DB_PATH  # noqa: F401  (legacy import target)


def main():
    from game.main import run
    run()


if __name__ == "__main__":
    main()
