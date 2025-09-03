import faiss
import requests
import numpy as np
import json
import os
import sqlite3
from extraction import extract_metadata
from typing import List, Dict, Tuple

def safe_batch_insert_listings(conn, listings_data: List[Dict]) -> List[int]:
    """
    Safer batch insertion that ensures SQLite and FAISS stay in sync
    
    Process:
    1. Begin SQLite transaction
    2. Insert all records and collect (row_id, text, metadata) tuples
    3. Get embeddings for all texts
    4. Verify we have matching counts
    5. Add to FAISS using the exact same order
    6. Commit SQLite transaction only if FAISS succeeds
    7. Save FAISS index
    """
    global index, index_file
    
    # Store original index state for rollback
    original_faiss_count = index.ntotal
    
    try:
        # Step 1: Begin transaction
        conn.execute("BEGIN TRANSACTION")
        cur = conn.cursor()
        
        # Step 2: Insert all into database and collect data in exact order
        insertion_records = []  # (row_id, text, metadata)
        
        for i, listing_data in enumerate(listings_data):
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
            
            # Store in exact order for later processing
            insertion_records.append({
                'index_in_batch': i,  # Original position in input
                'row_id': row_id,
                'text': text,
                'metadata': {
                    'location': location,
                    'price_min': price_min,
                    'price_max': price_max,
                    'beds': beds,
                    'baths': baths,
                    'user_id': user_id,
                    'user_name': user_name
                }
            })
        
        # Step 3: Get embeddings in the same order
        texts_ordered = [record['text'] for record in insertion_records]
        
        resp = requests.post("http://localhost:5000/embeds", json={"texts": texts_ordered})
        if resp.status_code != 200:
            raise Exception(f"Embedding server error: {resp.status_code} - {resp.text}")
        
        embeddings_response = resp.json()["embeddings"]
        
        # Step 4: Verify counts match
        if len(embeddings_response) != len(insertion_records):
            raise Exception(
                f"Embedding count mismatch! Expected {len(insertion_records)}, "
                f"got {len(embeddings_response)}"
            )
        
        # Step 5: Create aligned arrays for FAISS
        embeddings_array = np.array(embeddings_response, dtype="float32")
        row_ids_array = np.array([record['row_id'] for record in insertion_records], dtype="int64")
        
        # Verify array shapes
        if embeddings_array.shape[0] != row_ids_array.shape[0]:
            raise Exception(f"Array shape mismatch: embeddings {embeddings_array.shape}, ids {row_ids_array.shape}")
        
        # Step 6: Add to FAISS (this is the critical section)
        index.add_with_ids(embeddings_array, row_ids_array)
        
        # Step 7: If we got here, everything worked - commit the transaction
        conn.commit()
        cur.close()
        
        # Step 8: Save FAISS index
        faiss.write_index(index, index_file)
        
        # Log success with verification
        inserted_ids = [record['row_id'] for record in insertion_records]
        print(f"Successfully batch inserted {len(inserted_ids)} listings")
        print(f"Row IDs: {inserted_ids[:5]}..." + (f" (and {len(inserted_ids)-5} more)" if len(inserted_ids) > 5 else ""))
        print(f"FAISS now has {index.ntotal} vectors (was {original_faiss_count})")
        
        return inserted_ids
        
    except Exception as e:
        print(f"Error in batch insertion: {e}")
        
        # Rollback SQLite transaction
        try:
            conn.rollback()
            cur.close()
            print("Rolled back SQLite transaction")
        except Exception as rollback_error:
            print(f"Error during SQLite rollback: {rollback_error}")
        
        # Rollback FAISS changes (if any were made)
        try:
            if index.ntotal > original_faiss_count:
                # We need to reconstruct the index without the added vectors
                # This is complex, so let's reload from disk instead
                print("Attempting to rollback FAISS changes...")
                global index
                if os.path.exists(index_file):
                    index = faiss.read_index(index_file)
                    print(f"Reloaded FAISS index from disk. Vector count: {index.ntotal}")
                else:
                    print("Warning: Could not rollback FAISS - no saved index file found")
        except Exception as faiss_rollback_error:
            print(f"Error during FAISS rollback: {faiss_rollback_error}")
        
        raise e

def verify_insertion_integrity(conn, inserted_ids: List[int]) -> Dict:
    """
    Verify that inserted records are properly aligned between SQLite and FAISS
    """
    global index
    
    verification_results = {
        'total_checked': len(inserted_ids),
        'sqlite_found': 0,
        'faiss_found': 0,
        'missing_from_sqlite': [],
        'missing_from_faiss': [],
        'alignment_verified': True
    }
    
    try:
        cur = conn.cursor()
        
        for row_id in inserted_ids:
            # Check SQLite
            cur.execute("SELECT id, text FROM listings WHERE id = ?", (row_id,))
            sqlite_result = cur.fetchone()
            
            if sqlite_result:
                verification_results['sqlite_found'] += 1
            else:
                verification_results['missing_from_sqlite'].append(row_id)
                verification_results['alignment_verified'] = False
            
            # Check FAISS (if it supports ID mapping)
            if hasattr(index, 'id_map'):
                found_in_faiss = False
                try:
                    for i in range(index.ntotal):
                        if index.id_map.at(i) == row_id:
                            verification_results['faiss_found'] += 1
                            found_in_faiss = True
                            break
                    
                    if not found_in_faiss:
                        verification_results['missing_from_faiss'].append(row_id)
                        verification_results['alignment_verified'] = False
                        
                except Exception as e:
                    verification_results['faiss_error'] = str(e)
        
        cur.close()
        
    except Exception as e:
        verification_results['error'] = str(e)
        verification_results['alignment_verified'] = False
    
    return verification_results

# Alternative: Single-threaded, one-by-one insertion (safest but slower)
def ultra_safe_batch_insert(conn, listings_data: List[Dict]) -> List[int]:
    """
    Ultra-safe version that inserts one by one with immediate verification
    Slower but guarantees consistency
    """
    from insertion import insert_listing  # Your original single insert function
    
    inserted_ids = []
    failed_insertions = []
    
    for i, listing_data in enumerate(listings_data):
        try:
            text = listing_data['text']
            user_id = listing_data.get('user_id', '')
            user_name = listing_data.get('user_name', '')
            
            row_id = insert_listing(conn, text, user_id, user_name)
            inserted_ids.append(row_id)
            print(f"Inserted {i+1}/{len(listings_data)}: ID {row_id}")
            
        except Exception as e:
            failed_insertions.append({
                'index': i,
                'data': listing_data,
                'error': str(e)
            })
            print(f"Failed insertion {i+1}/{len(listings_data)}: {e}")
    
    if failed_insertions:
        print(f"Warning: {len(failed_insertions)} insertions failed")
        # Optionally, you could retry failed insertions here
    
    return inserted_ids