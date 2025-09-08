import sqlite3

def get_equipped_artifact():
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT artifact_id FROM equipped WHERE id=1")
        result = c.fetchone()
        return result[0] if result else None

def set_equipped_artifact(artifact_id):
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE equipped SET artifact_id=? WHERE id=1", (artifact_id,))
        conn.commit()