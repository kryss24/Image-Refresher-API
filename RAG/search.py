def search(conn, query, max_price=None, min_beds=None, top_k=5):
    # Hard filters in SQLite
    sql = "SELECT id, text FROM listings WHERE 1=1"
    params = []
    if max_price:
        sql += " AND price_min <= ?"
        params.append(max_price)
    if min_beds:
        sql += " AND beds >= ?"
        params.append(min_beds)

    cur = conn.cursor()
    cur.execute(sql, params)
    candidates = cur.fetchall()

    if not candidates:
        return []

    # Embed query
    resp = requests.post("http://localhost:5000/embed", json={"text": query})
    query_vec = np.array(resp.json()["embedding"], dtype="float32").reshape(1, -1)

    # Restrict FAISS search to candidate IDs
    candidate_ids = np.array([c[0] for c in candidates], dtype="int64")
    candidate_vecs = index.reconstruct_n(0, index.ntotal)  # Get all vectors
    sub_index = faiss.IndexIDMap(faiss.IndexFlatL2(dim))
    sub_index.add_with_ids(candidate_vecs, candidate_ids)

    D, I = sub_index.search(query_vec, top_k)

    results = []
    for dist, idx in zip(D[0], I[0]):
        cur.execute("SELECT * FROM listings WHERE id=?", (int(idx),))
        results.append({"distance": float(dist), "listing": cur.fetchone()})

    return results
