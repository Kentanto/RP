"""Sync the content definition files (data/*.txt) into the database.

The game syncs these automatically on every start; run this manually
after editing definitions if you want to check them without launching:

    python init_items.py
"""
from game import db


def main():
    db.initialize_database()          # includes the content sync, idempotent
    items = db.get_item_defs()
    artifacts = db.get_artifact_defs()
    print(f"Synced {len(items)} item definitions and "
          f"{len(artifacts)} artifact archetypes into the database.")
    for item in items:
        tag = " [special]" if item["category"] == "special" else ""
        print(f"  item     {item['name']} ({item['rarity']} {item['type']}){tag}")
    for artifact in artifacts:
        print(f"  artifact {artifact['name']} ({artifact['rarity']})")


if __name__ == "__main__":
    main()
