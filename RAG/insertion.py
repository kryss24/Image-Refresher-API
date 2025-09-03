import faiss
import requests
import numpy as np
import json
from extraction import extract_metadata

# Initialize FAISS index (dimension = 384 for MiniLM)
dim = 384
index = faiss.IndexFlatL2(dim)

def insert_listing(conn, text, user_id, user_name):
    # Extract metadata
    price_min, price_max, beds, baths, location = extract_metadata(text)

    # Insert into SQLite
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO listings (text, location, price_min, price_max, beds, baths, user_id, user_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (text, location, price_min, price_max, beds, baths, user_id, user_name))
    conn.commit()
    row_id = cur.lastrowid

    # Get embedding from your embedding server
    resp = requests.post("http://localhost:5000/embed", json={"text": text})
    embedding = np.array(resp.json()["embedding"], dtype="float32")

    # Add to FAISS with SQLite row_id as mapping
    index.add_with_ids(np.array([embedding]), np.array([row_id], dtype="int64"))

    return row_id
