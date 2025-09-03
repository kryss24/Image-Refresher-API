import faiss
import numpy as np
import requests
import sqlite3
from insertion import get_or_create_index, dim # Assuming dim is defined here

def search(conn, query, max_price=None, min_beds=None, top_k=5):
    # Step 1: Perform the full FAISS search first
    index = get_or_create_index()
    
    # Embed the query
    resp = requests.post("http://localhost:5000/embed", json={"text": query})
    query_vec = np.array(resp.json()["embedding"], dtype="float32").reshape(1, -1)
    
    # Search the full FAISS index for a larger number of candidates
    # We retrieve more than top_k to account for filtering
    # For example, search for 20 candidates and then filter down to the best 5
    search_k = top_k * 5
    D, I = index.search(query_vec, search_k)

    # Step 2: Retrieve the ID-text pairs for filtering
    # Get the raw candidate data from the database using the hard filters
    sql = "SELECT id FROM listings WHERE 1=1"
    params = []
    if max_price:
        sql += " AND price_min <= ?"
        params.append(max_price)
    if min_beds:
        sql += " AND beds >= ?"
        params.append(min_beds)

    cur = conn.cursor()
    cur.execute(sql, params)
    
    # Convert candidates from a list of tuples to a set for fast lookups
    valid_ids = {row[0] for row in cur.fetchall()}

    # Step 3: Post-filter the FAISS results
    results = []
    for dist, idx in zip(D[0], I[0]):
        # Check if the FAISS result ID is in our list of valid database candidates
        if idx in valid_ids:
            cur.execute("SELECT * FROM listings WHERE id=?", (int(idx),))
            results.append({"distance": float(dist), "listing": cur.fetchone()})
            if len(results) >= top_k:
                break # Stop once we have our desired number of results

    return results

