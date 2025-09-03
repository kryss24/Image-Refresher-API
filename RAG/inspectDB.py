import sqlite3
import faiss
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime

class DatabaseInspector:
    def __init__(self, db_path: str, faiss_index_path: str):
        self.db_path = db_path
        self.faiss_index_path = faiss_index_path
        
    def get_sqlite_connection(self):
        """Get SQLite connection"""
        return sqlite3.connect(self.db_path)
    
    def load_faiss_index(self):
        """Load FAISS index"""
        try:
            return faiss.read_index(self.faiss_index_path)
        except Exception as e:
            print(f"Error loading FAISS index: {e}")
            return None
    
    def sqlite_stats(self) -> Dict:
        """Get SQLite database statistics"""
        conn = self.get_sqlite_connection()
        cur = conn.cursor()
        
        stats = {}
        
        try:
            # Get table info
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cur.fetchall()]
            stats['tables'] = tables
            
            # Get listings table stats
            if 'listings' in tables:
                cur.execute("SELECT COUNT(*) FROM listings")
                stats['total_listings'] = cur.fetchone()[0]
                
                cur.execute("SELECT MIN(id), MAX(id) FROM listings")
                min_id, max_id = cur.fetchone()
                stats['id_range'] = {'min': min_id, 'max': max_id}
                
                # Check for gaps in IDs
                cur.execute("""
                    SELECT id + 1 as gap_start
                    FROM listings mo
                    WHERE NOT EXISTS (SELECT NULL FROM listings mi WHERE mi.id = mo.id + 1)
                    AND mo.id < (SELECT MAX(id) FROM listings)
                """)
                gaps = [row[0] for row in cur.fetchall()]
                stats['id_gaps'] = gaps[:10]  # Show first 10 gaps
                
                # Price statistics
                cur.execute("SELECT MIN(price_min), MAX(price_max), AVG(price_min) FROM listings WHERE price_min IS NOT NULL")
                price_stats = cur.fetchone()
                if price_stats[0] is not None:
                    stats['price_stats'] = {
                        'min_price': price_stats[0],
                        'max_price': price_stats[1],
                        'avg_price': round(price_stats[2], 2)
                    }
                
                # Beds/baths stats
                cur.execute("SELECT beds, COUNT(*) FROM listings WHERE beds IS NOT NULL GROUP BY beds ORDER BY beds")
                beds_distribution = dict(cur.fetchall())
                stats['beds_distribution'] = beds_distribution
                
                # User stats
                cur.execute("SELECT COUNT(DISTINCT user_id) FROM listings WHERE user_id IS NOT NULL AND user_id != ''")
                stats['unique_users'] = cur.fetchone()[0]
                
        except Exception as e:
            stats['error'] = str(e)
        finally:
            conn.close()
        
        return stats
    
    def faiss_stats(self) -> Dict:
        """Get FAISS index statistics"""
        index = self.load_faiss_index()
        if index is None:
            return {'error': 'Could not load FAISS index'}
        
        stats = {
            'total_vectors': index.ntotal,
            'dimension': index.d,
            'index_type': type(index).__name__,
            'is_trained': index.is_trained,
        }
        
        # If it's an IndexIDMap, get the underlying index info
        if hasattr(index, 'index'):
            stats['base_index_type'] = type(index.index).__name__
        
        return stats
    
    def check_consistency(self) -> Dict:
        """Check consistency between SQLite and FAISS"""
        conn = self.get_sqlite_connection()
        index = self.load_faiss_index()
        
        if index is None:
            return {'error': 'Could not load FAISS index'}
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'sqlite_count': 0,
            'faiss_count': index.ntotal,
            'missing_in_faiss': [],
            'extra_in_faiss': [],
            'consistency_ok': False
        }
        
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM listings ORDER BY id")
            sqlite_ids = [row[0] for row in cur.fetchall()]
            results['sqlite_count'] = len(sqlite_ids)
            
            # For IndexIDMap, we can get the IDs
            if hasattr(index, 'id_map'):
                # Get all IDs from FAISS
                faiss_ids = []
                for i in range(index.ntotal):
                    faiss_ids.append(index.id_map.at(i))
                
                sqlite_set = set(sqlite_ids)
                faiss_set = set(faiss_ids)
                
                results['missing_in_faiss'] = list(sqlite_set - faiss_set)
                results['extra_in_faiss'] = list(faiss_set - sqlite_set)
                results['consistency_ok'] = len(results['missing_in_faiss']) == 0 and len(results['extra_in_faiss']) == 0
            else:
                results['note'] = 'Cannot check ID consistency - index does not support ID mapping'
        
        except Exception as e:
            results['error'] = str(e)
        finally:
            conn.close()
        
        return results
    
    def sample_data(self, limit: int = 5) -> Dict:
        """Get sample data from both SQLite and FAISS"""
        conn = self.get_sqlite_connection()
        index = self.load_faiss_index()
        
        results = {'sqlite_samples': [], 'faiss_info': {}}
        
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, text, location, price_min, beds, user_name FROM listings LIMIT ?", (limit,))
            
            for row in cur.fetchall():
                results['sqlite_samples'].append({
                    'id': row[0],
                    'text': row[1][:100] + '...' if len(row[1]) > 100 else row[1],
                    'location': row[2],
                    'price_min': row[3],
                    'beds': row[4],
                    'user_name': row[5]
                })
            
            if index:
                results['faiss_info'] = {
                    'total_vectors': index.ntotal,
                    'vector_dimension': index.d,
                    'sample_vector_norms': []
                }
                
                # Get a few vector norms as samples
                if index.ntotal > 0:
                    for i in range(min(3, index.ntotal)):
                        vector = index.reconstruct(i)
                        norm = np.linalg.norm(vector)
                        results['faiss_info']['sample_vector_norms'].append(float(norm))
        
        except Exception as e:
            results['error'] = str(e)
        finally:
            conn.close()
        
        return results
    
    def find_duplicates(self) -> Dict:
        """Find potential duplicate entries"""
        conn = self.get_sqlite_connection()
        
        results = {
            'exact_text_duplicates': [],
            'similar_listings': []
        }
        
        try:
            cur = conn.cursor()
            
            # Find exact text duplicates
            cur.execute("""
                SELECT text, COUNT(*) as count, GROUP_CONCAT(id) as ids
                FROM listings 
                GROUP BY text 
                HAVING count > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            
            for row in cur.fetchall():
                results['exact_text_duplicates'].append({
                    'text': row[0][:100] + '...' if len(row[0]) > 100 else row[0],
                    'count': row[1],
                    'ids': row[2]
                })
        
        except Exception as e:
            results['error'] = str(e)
        finally:
            conn.close()
        
        return results
    
    def search_by_id(self, listing_id: int) -> Dict:
        """Get detailed info about a specific listing"""
        conn = self.get_sqlite_connection()
        index = self.load_faiss_index()
        
        result = {'listing_id': listing_id}
        
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
            row = cur.fetchone()
            
            if row:
                cur.execute("PRAGMA table_info(listings)")
                columns = [col[1] for col in cur.fetchall()]
                result['sqlite_data'] = dict(zip(columns, row))
                
                # Try to find in FAISS
                if index and hasattr(index, 'id_map'):
                    try:
                        # This is a bit tricky - we need to find the internal index
                        for i in range(index.ntotal):
                            if index.id_map.at(i) == listing_id:
                                vector = index.reconstruct(i)
                                result['faiss_data'] = {
                                    'internal_index': i,
                                    'vector_norm': float(np.linalg.norm(vector)),
                                    'vector_preview': vector[:10].tolist()  # First 10 dimensions
                                }
                                break
                        else:
                            result['faiss_data'] = {'status': 'ID not found in FAISS'}
                    except Exception as e:
                        result['faiss_data'] = {'error': str(e)}
            else:
                result['sqlite_data'] = {'status': 'ID not found in SQLite'}
        
        except Exception as e:
            result['error'] = str(e)
        finally:
            conn.close()
        
        return result
    
    def generate_report(self) -> str:
        """Generate a comprehensive report"""
        report = []
        report.append("=== DATABASE INSPECTION REPORT ===")
        report.append(f"Generated at: {datetime.now()}")
        report.append("")
        
        # SQLite stats
        report.append("--- SQLite Statistics ---")
        sqlite_stats = self.sqlite_stats()
        for key, value in sqlite_stats.items():
            report.append(f"{key}: {value}")
        report.append("")
        
        # FAISS stats
        report.append("--- FAISS Statistics ---")
        faiss_stats = self.faiss_stats()
        for key, value in faiss_stats.items():
            report.append(f"{key}: {value}")
        report.append("")
        
        # Consistency check
        report.append("--- Consistency Check ---")
        consistency = self.check_consistency()
        for key, value in consistency.items():
            report.append(f"{key}: {value}")
        report.append("")
        
        # Duplicates
        report.append("--- Duplicate Check ---")
        duplicates = self.find_duplicates()
        if duplicates['exact_text_duplicates']:
            report.append("Found exact text duplicates:")
            for dup in duplicates['exact_text_duplicates'][:5]:
                report.append(f"  - {dup['count']} copies: {dup['text']}")
        else:
            report.append("No exact text duplicates found")
        
        return "\n".join(report)

# Usage example and CLI interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python inspector.py <sqlite_db_path> <faiss_index_path> [command]")
        print("Commands: stats, consistency, sample, duplicates, report, search <id>")
        sys.exit(1)
    
    inspector = DatabaseInspector(sys.argv[1], sys.argv[2])
    command = sys.argv[3] if len(sys.argv) > 3 else 'report'
    
    if command == 'stats':
        print("SQLite Stats:")
        print(json.dumps(inspector.sqlite_stats(), indent=2))
        print("\nFAISS Stats:")
        print(json.dumps(inspector.faiss_stats(), indent=2))
    
    elif command == 'consistency':
        print(json.dumps(inspector.check_consistency(), indent=2))
    
    elif command == 'sample':
        print(json.dumps(inspector.sample_data(), indent=2))
    
    elif command == 'duplicates':
        print(json.dumps(inspector.find_duplicates(), indent=2))
    
    elif command == 'search' and len(sys.argv) > 4:
        listing_id = int(sys.argv[4])
        print(json.dumps(inspector.search_by_id(listing_id), indent=2))
    
    elif command == 'report':
        print(inspector.generate_report())
    
    else:
        print("Unknown command or missing parameters")