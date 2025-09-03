import sqlite3

def init_db():
    conn = sqlite3.connect("uga.db")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        location TEXT,
        price_min REAL,
        price_max REAL,
        beds INTEGER,
        baths INTEGER,
        user_id TEXT,
        user_name TEXT
    );
    """)
    conn.commit()
    return conn
