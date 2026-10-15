import sqlite3
import os

from game.settings import DB_PATH

def init_items():
    items = [
        ('Health Potion', 'Restores 50 HP', 'consumable', 'common'),
        ('Mana Crystal', 'Grants 100 mana', 'consumable', 'uncommon'),
        ('Dragon Scale', 'A rare crafting material', 'material', 'rare'),
        ('Ancient Scroll', 'Contains forgotten wisdom', 'quest', 'epic'),
        ('Phoenix Feather', 'A legendary crafting component', 'material', 'legendary')
    ]

    shop_items = [
        (1, 100, 10),  # Health Potion - 100 points, 10 in stock
        (2, 200, 5),   # Mana Crystal - 200 points, 5 in stock
        (3, 500, 3),   # Dragon Scale - 500 points, 3 in stock
        (4, 1000, 1),  # Ancient Scroll - 1000 points, 1 in stock
        (5, 2000, 1)   # Phoenix Feather - 2000 points, 1 in stock
    ]

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        
        # Clear existing data
        c.execute("DELETE FROM shop_inventory")
        c.execute("DELETE FROM inventory")
        c.execute("DELETE FROM items")
        
        # Add items
        c.executemany("INSERT INTO items (name, description, type, rarity) VALUES (?, ?, ?, ?)", items)
        
        # Add items to shop
        c.executemany("INSERT INTO shop_inventory (item_id, price, quantity) VALUES (?, ?, ?)", shop_items)
        
        conn.commit()
        print("Items initialized successfully!")

if __name__ == "__main__":
    init_items()