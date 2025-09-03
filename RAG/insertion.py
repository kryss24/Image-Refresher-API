import faiss
import requests
import numpy as np
import json
import os
from extraction import extract_metadata

# Initialize FAISS index (dimension = 384 for MiniLM)
dim = 384
index_file = 'faiss_listings_index.idx'

def get_or_create_index():
    """Get existing index or create new one with ID support"""
    global index_file, dim
    
    if os.path.exists(index_file):
        # Load existing index
        try:
            index = faiss.read_index(index_file)
            print(f"Loaded existing FAISS index with {index.ntotal} vectors")
            return index
        except Exception as e:
            print(f"Error loading index: {e}, creating new one...")
    
    # Create new index with ID support
    base_index = faiss.IndexFlatL2(dim)
    index = faiss.IndexIDMap(base_index)  # This wrapper enables add_with_ids
    
    # Save the empty index
    faiss.write_index(index, index_file)
    print("Created new FAISS index with ID support")
    return index

# Initialize index once when module is imported
index = get_or_create_index()

def insert_listing(conn, text, user_id, user_name):
    global index, index_file
    
    try:
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
        cur.close()

        # Get embedding from your embedding server
        resp = requests.post("http://localhost:5000/embed", json={"text": text})
        if resp.status_code != 200:
            raise Exception(f"Embedding server error: {resp.status_code}")
            
        embedding = np.array(resp.json()["embedding"], dtype="float32")

        # Add to FAISS with SQLite row_id as mapping
        index.add_with_ids(np.array([embedding]), np.array([row_id], dtype="int64"))
        
        # Save updated index to disk
        faiss.write_index(index, index_file)
        
        print(f"Successfully inserted listing {row_id}")
        return row_id
        
    except Exception as e:
        print(f"Error inserting listing: {e}")
        # Rollback database changes if something went wrong
        if 'row_id' in locals():
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM listings WHERE id = ?", (row_id,))
                conn.commit()
                cur.close()
                print(f"Rolled back database insertion for row {row_id}")
            except Exception as rollback_error:
                print(f"Error during rollback: {rollback_error}")
        raise e

def batch_insert_listings(conn, listings_data):
    """
    More efficient batch insertion
    listings_data: list of dicts with keys: text, user_id, user_name
    """
    global index, index_file
    
    try:
        cur = conn.cursor()
        inserted_rows = []
        texts_for_embedding = []
        
        # First, insert all into database
        for listing_data in listings_data:
            text = listing_data['text']
            user_id = listing_data.get('user_id', '')
            user_name = listing_data.get('user_name', '')
            
            # Extract metadata
            price_min, price_max, beds, baths, location = extract_metadata(text)
            
            # Insert into SQLite
            cur.execute("""
                INSERT INTO listings (text, location, price_min, price_max, beds, baths, user_id, user_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (text, location, price_min, price_max, beds, baths, user_id, user_name))
            
            row_id = cur.lastrowid
            inserted_rows.append(row_id)
            texts_for_embedding.append(text)
        
        conn.commit()
        cur.close()
        
        # Get embeddings in batch (more efficient)
        resp = requests.post("http://localhost:5000/embeds", json={"texts": texts_for_embedding})
        if resp.status_code != 200:
            raise Exception(f"Embedding server error: {resp.status_code}")
            
        embeddings = np.array(resp.json()["embeddings"], dtype="float32")
        row_ids_array = np.array(inserted_rows, dtype="int64")
        
        # Add all to FAISS at once
        index.add_with_ids(embeddings, row_ids_array)
        
        # Save updated index
        faiss.write_index(index, index_file)
        
        print(f"Successfully batch inserted {len(inserted_rows)} listings")
        return inserted_rows
        
    except Exception as e:
        print(f"Error in batch insertion: {e}")
        # Rollback database changes
        if 'inserted_rows' in locals() and inserted_rows:
            try:
                cur = conn.cursor()
                placeholders = ','.join(['?' for _ in inserted_rows])
                cur.execute(f"DELETE FROM listings WHERE id IN ({placeholders})", inserted_rows)
                conn.commit()
                cur.close()
                print(f"Rolled back {len(inserted_rows)} database insertions")
            except Exception as rollback_error:
                print(f"Error during rollback: {rollback_error}")
        raise e

def get_index_stats():
    """Get statistics about the current index"""
    global index
    return {
        "total_vectors": index.ntotal,
        "dimension": index.d,
        "index_type": type(index).__name__
    }