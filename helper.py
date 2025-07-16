### helpers.py

import json
import os
import requests
#from firebase_admin import storage, firestore

# Initialize Firebase storage bucket (should be called once at app startup)
# firebase_utils.py
from firebase_admin import credentials, initialize_app, firestore, storage, get_app
import firebase_admin

def init_firebase(bucket_name: str, cred_path: str = None):
    """
    Initialize Firebase Admin SDK and return Firestore DB and Storage Bucket.
    
    :param bucket_name: Firebase Storage bucket name (e.g. 'your-project-id.appspot.com')
    :param cred_path: Path to the service account key JSON (optional if ENV-based authentication is used)
    :return: Dict with Firestore client and Storage bucket
    """
    try:
        # Only initialize once
        if not firebase_admin._apps:
            if cred_path:
                cred = credentials.Certificate(cred_path)
                initialize_app(cred, {'storageBucket': bucket_name})
            else:
                initialize_app(options={'storageBucket': bucket_name})

        db = firestore.client()
        bucket =storage.bucket()
        return {"db": db, "bucket": bucket}

    except Exception as e:
        # Handle error gracefully (can replace with logging or raise)
        raise RuntimeError(f"Firebase initialization failed: {e}")



def extract_image_urls(listing: dict) -> list:
    """
    Extracts all image URLs from a single listing's attachments.
    :param listing: A dict representing a single listing
    :return: List of URL strings
    """
    urls = []
    for attachment in listing.get('attachments', []):
        # Prefer full-size image URI if available, fallback to thumbnail
        image = attachment.get('image') or attachment.get('photo_image')
        if image and 'uri' in image:
            urls.append(image['uri'])
        elif attachment.get('thumbnail'):
            urls.append(attachment['thumbnail'])
    return urls


def download_image(url: str) -> bytes:
    """
    Downloads an image from the given URL and returns its bytes.
    :param url: URL of the image to download
    :return: Image binary data
    """
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def upload_to_firebase(bucket, data: bytes, destination_path: str) -> str:
    """
    Uploads binary data to Firebase Storage and returns the public download URL.
    :param bucket: Firebase Storage bucket instance
    :param data: Binary data of file
    :param destination_path: Path in the bucket to store the file
    :return: Public URL of the uploaded file
    """
    blob = bucket.blob(destination_path)
    blob.upload_from_string(data)
    # Optionally make public
    blob.make_public()
    return blob.public_url


def process_listings(payload: list, bucket) -> list:
    """
    Process a list of listings: downloads images, uploads to Firebase, and augments listings.
    :param payload: List of listing dicts
    :param bucket: Firebase Storage bucket instance
    :return: Augmented list of listings
    """
    processed = []
    for idx, listing in enumerate(payload):
        new_listing = listing.copy()
        firebase_urls = []

        urls = extract_image_urls(listing)
        for j, url in enumerate(urls):
            image_data = download_image(url)
            # Create a unique storage path: e.g. listings/{idx}/image_{j}.jpg
            extension = os.path.splitext(url)[1].split('?')[0] or '.jpg'
            dest_path = f'listings/{idx}/image_{j}{extension}'
            public_url = upload_to_firebase(bucket, image_data, dest_path)
            firebase_urls.append(public_url)

        # Add new field
        new_listing['firebase_images'] = firebase_urls
        processed.append(new_listing)

    return processed