from flask import Flask, request, jsonify
from pydantic import RootModel, ValidationError
from typing import List, Dict, Any
import os

import firebase_admin
from firebase_admin import credentials

from helper import init_firebase, process_listings

# Pydantic model to validate incoming data
class ListingModel(RootModel[List[Dict[str, Any]]]):
    pass

# Load environment variables
FIREBASE_BUCKET = 'subleasa-7a3de.firebasestorage.app' #os.getenv('FIREBASE_BUCKET')
FIREBASE_CRED = './subleasa-7a3de-firebase-adminsdk-fbsvc-329f659da8.json' #os.getenv('GOOGLE_APPLICATION_CREDENTIALS')  # path to service account JSON

# Initialize Flask app
app = Flask(__name__)

# Initialize Firebase bucket (singleton)
def get_bucket():
    if not firebase_admin._apps:
        if not FIREBASE_BUCKET:
            raise RuntimeError("FIREBASE_BUCKET environment variable not set")
        result = init_firebase(bucket_name=FIREBASE_BUCKET, cred_path=FIREBASE_CRED)
    return result

FIREBASE_VAR = get_bucket()
db = FIREBASE_VAR['db']
bucket = FIREBASE_VAR['bucket']
@app.route('/process', methods=['POST'])
def process_endpoint():
    """
    API endpoint to process listings: extracts image URLs, uploads to Firebase, and returns augmented data.
    """
    try:
        # Validate incoming JSON with Pydantic
        raw = request.get_json(force=True)
        listings = ListingModel(__root__=raw)
    except ValidationError as ve:
        return jsonify({'error': ve.errors()}), 400
    except Exception as e:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    try:
        bucket = get_bucket()
        result = process_listings(listings.__root__, bucket)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/collections', methods=['GET'])
def list_collections():
    try:
       
        collections = db.collections()
        collection_names = [col.id for col in collections]
        return jsonify({'collections': collection_names}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check route for Firestore DB and Firebase Storage.
    """
    try:
        # Check Firestore (attempt to list collections)
        collections = list(db.collections())
        db_status = "ready" if collections is not None else "unavailable"
    except Exception as db_exc:
        db_status = f"error: {db_exc}"

    try:
        # Check Storage (attempt to list blobs)
        blobs = list(bucket.list_blobs(max_results=1))
        bucket_status = "ready" if blobs is not None else "unavailable"
    except Exception as bucket_exc:
        bucket_status = f"error: {bucket_exc}"

    status = {
        "firestore": db_status,
        "storage_bucket": bucket_status
    }
    all_healthy = db_status == "ready" and bucket_status == "ready"
    return jsonify({
        "status": "healthy" if all_healthy else "unhealthy",
        "components": status
    }), (200 if all_healthy else 500)


if __name__ == '__main__':
    # Default Flask port
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)