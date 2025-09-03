from db import init_db
from insertion import insert_listing
from search import search
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from flask_cors import CORS
import sqlite3
import threading

# Initialize Flask app and enable CORS
app = Flask(__name__)
CORS(app)

# Thread-local storage for database connections
thread_local = threading.local()

def get_db_connection():
    """Get a thread-local database connection"""
    if not hasattr(thread_local, 'conn'):
        thread_local.conn = init_db()
    return thread_local.conn

# Load the sentence-transformers model only when needed
model = None

def get_model():
    """Lazy load the sentence-transformers model"""
    global model
    if model is None:
        model = SentenceTransformer('all-MiniLM-L6-v2')
    return model

@app.route('/embed', methods=['POST'])
def embed_single():
    """
    Endpoint to embed a single text input.
    Request JSON: { "text": "Your text here" }
    Response JSON: { "embedding": [float, ...] }
    """
    data = request.get_json()
    text = data.get('text')
    if not text or not isinstance(text, str):
        return jsonify({'error': 'No valid text provided.'}), 400

    # Compute embedding using lazy-loaded model
    vector = get_model().encode(text)
    return jsonify({'embedding': vector.tolist()})

@app.route('/embeds', methods=['POST'])
def embed_batch():
    """
    Endpoint to embed an array of text inputs.
    Request JSON: { "texts": ["text1", "text2", ...] }
    Response JSON: { "embeddings": [[float, ...], ...] }
    """
    data = request.get_json()
    texts = data.get('texts')
    if not texts or not isinstance(texts, list):
        return jsonify({'error': 'No valid texts list provided.'}), 400

    # Compute embeddings using lazy-loaded model
    vectors = get_model().encode(texts)
    return jsonify({'embeddings': [vec.tolist() for vec in vectors]})

@app.route("/insert", methods=["POST"])
def insert():
    data = request.json
    text = data["text"]
    user_id = data.get("user_id", "")
    user_name = data.get("user_name", "")
    conn = get_db_connection()
    row_id = insert_listing(conn, text, user_id, user_name)
    return jsonify({"id": row_id})

@app.route("/batchInsertion", methods=["POST"])
def batch_insertion():
    data = request.json # contains a list of listings
    inserted_ids = []
    conn = get_db_connection()
    for listing in data:
        text = listing["text"]
        user_id = listing["user"]["id"] if "user" in listing and "id" in listing["user"] else ""
        user_name = listing["user"]["name"] if "user" in listing and "name" in listing["user"] else ""
        row_id = insert_listing(conn, text, user_id, user_name)
        inserted_ids.append(row_id)
    return jsonify({"inserted_ids": inserted_ids})

@app.route("/search", methods=["POST"])
def search_api():
    data = request.json
    query = data["query"]
    max_price = data.get("max_price")
    min_beds = data.get("min_beds")
    conn = get_db_connection()
    results = search(conn, query, max_price, min_beds)
    return jsonify(results)

if __name__ == '__main__':
    # Run the Flask development server (for production, use a WSGI server like gunicorn)
    app.run(host='0.0.0.0', port=5000, debug=True)