import os
import firebase_admin
from firebase_admin import credentials, storage
import logging

logger = logging.getLogger(__name__)

class FirebaseStorageManager:
    def __init__(self):
        self.bucket = None
        self._initialize_firebase()

    def _initialize_firebase(self):
        try:
            if not firebase_admin._apps:
                if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                    cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
                elif os.path.exists("firebase-credentials.json"):
                    cred = credentials.Certificate("firebase-credentials.json")
                else:
                    raise Exception("Firebase credentials not found")
                print(cred)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': "subleasa-7a3de.firebasestorage.app.appspot.com"
                })

            self.bucket = storage.bucket()
            logger.info(f"Firebase initialized with bucket: {self.bucket.name}")

        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
            raise

    def upload_image(self, image_data, filename, content_type="image/jpeg"):
        try:
            blob = self.bucket.blob(filename)
            blob.upload_from_string(image_data, content_type=content_type)
            blob.make_public()
            logger.info(f"Uploaded {filename}")
            return blob.public_url
        except Exception as e:
            logger.error(f"Upload failed for {filename}: {e}")
            raise

    def delete_image(self, filename):
        try:
            blob = self.bucket.blob(filename)
            blob.delete()
            logger.info(f"Deleted {filename}")
            return True
        except Exception as e:
            logger.error(f"Delete failed for {filename}: {e}")
            return False

    def list_images(self, prefix="marketplace_images/"):
        try:
            blobs = self.bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"List failed: {e}")
            return []

# Singleton pattern
_firebase_manager = None

def get_firebase_manager():
    global _firebase_manager
    if _firebase_manager is None:
        _firebase_manager = FirebaseStorageManager()
    return _firebase_manager

def upload_image_to_firebase(image_data, filename, content_type=None):
    return get_firebase_manager().upload_image(image_data, filename, content_type)

def delete_image_from_firebase(filename):
    return get_firebase_manager().delete_image(filename)

def list_firebase_images(prefix="marketplace_images/"):
    return get_firebase_manager().list_images(prefix)
