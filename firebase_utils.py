import os
import logging
from google.cloud import storage
from google.oauth2 import service_account
import json
from io import BytesIO

logger = logging.getLogger(__name__)

class FirebaseStorageManager:
    """Manager class for Firebase Storage operations."""
    
    def __init__(self):
        self.client = None
        self.bucket = None
        self.bucket_name = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Storage client."""
        try:
            # Method 1: Try environment variable for credentials file path
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                logger.info("Using Firebase credentials from GOOGLE_APPLICATION_CREDENTIALS")
                self.client = storage.Client.from_service_account_json(credentials_path)
            
            # Method 2: Try local credentials file
            elif os.path.exists('firebase-credentials.json'):
                logger.info("Using Firebase credentials from firebase-credentials.json")
                self.client = storage.Client.from_service_account_json('firebase-credentials.json')
            
            # Method 3: Try environment variable with JSON content
            elif os.getenv('FIREBASE_CREDENTIALS_JSON'):
                logger.info("Using Firebase credentials from FIREBASE_CREDENTIALS_JSON environment variable")
                credentials_json = json.loads(os.getenv('FIREBASE_CREDENTIALS_JSON'))
                credentials = service_account.Credentials.from_service_account_info(credentials_json)
                self.client = storage.Client(credentials=credentials)
            
            # Method 4: Try default credentials (for Google Cloud environment)
            else:
                logger.info("Attempting to use default Firebase credentials")
                self.client = storage.Client()
            
            # Get bucket name from environment or use default
            self.bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET')
            if not self.bucket_name:
                raise ValueError("FIREBASE_STORAGE_BUCKET environment variable is required")
            
            # Remove .appspot.com if present (common mistake)
            if self.bucket_name.endswith('.appspot.com'):
                self.bucket_name = self.bucket_name.replace('.appspot.com', '')
                logger.info(f"Cleaned bucket name: {self.bucket_name}")
            
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"Successfully initialized Firebase Storage with bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Storage: {str(e)}")
            raise
    
    def upload_image(self, image_data, filename, content_type=None):
        """
        Upload image data to Firebase Storage.
        
        Args:
            image_data (bytes): Binary image data
            filename (str): Destination filename in storage
            content_type (str): MIME type of the image
        
        Returns:
            str: Public URL of uploaded image
        """
        try:
            if not self.bucket:
                raise RuntimeError("Firebase Storage not properly initialized")
            
            # Ensure filename doesn't start with /
            filename = filename.lstrip('/')
            
            # Create blob
            blob = self.bucket.blob(filename)
            
            # Determine content type if not provided
            if not content_type:
                if filename.lower().endswith('.png'):
                    content_type = 'image/png'
                elif filename.lower().endswith('.gif'):
                    content_type = 'image/gif'
                elif filename.lower().endswith('.webp'):
                    content_type = 'image/webp'
                else:
                    content_type = 'image/jpeg'
            
            # Upload with proper content type
            blob.upload_from_string(
                image_data,
                content_type=content_type
            )
            
            # Make blob publicly accessible
            blob.make_public()
            
            # Return public URL
            public_url = blob.public_url
            logger.info(f"Successfully uploaded image to: {public_url}")
            
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload image {filename}: {str(e)}")
            raise
    
    def delete_image(self, filename):
        """
        Delete an image from Firebase Storage.
        
        Args:
            filename (str): Filename to delete
        
        Returns:
            bool: True if successful
        """
        try:
            if not self.bucket:
                raise RuntimeError("Firebase Storage not properly initialized")
            
            filename = filename.lstrip('/')
            blob = self.bucket.blob(filename)
            blob.delete()
            
            logger.info(f"Successfully deleted image: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete image {filename}: {str(e)}")
            return False
    
    def list_images(self, prefix="marketplace_images/"):
        """
        List all images with given prefix.
        
        Args:
            prefix (str): Prefix to filter files
        
        Returns:
            list: List of blob names
        """
        try:
            if not self.bucket:
                raise RuntimeError("Firebase Storage not properly initialized")
            
            blobs = self.bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
            
        except Exception as e:
            logger.error(f"Failed to list images with prefix {prefix}: {str(e)}")
            return []

# Global instance
_firebase_manager = None

def get_firebase_manager():
    """Get or create Firebase Storage manager instance."""
    global _firebase_manager
    if _firebase_manager is None:
        _firebase_manager = FirebaseStorageManager()
    return _firebase_manager

def upload_image_to_firebase(image_data, filename, content_type=None):
    """
    Convenience function to upload image to Firebase Storage.
    
    Args:
        image_data (bytes): Binary image data
        filename (str): Destination filename
        content_type (str): MIME type of the image
    
    Returns:
        str: Public URL of uploaded image
    """
    manager = get_firebase_manager()
    return manager.upload_image(image_data, filename, content_type)

def delete_image_from_firebase(filename):
    """
    Convenience function to delete image from Firebase Storage.
    
    Args:
        filename (str): Filename to delete
    
    Returns:
        bool: True if successful
    """
    manager = get_firebase_manager()
    return manager.delete_image(filename)

def list_firebase_images(prefix="marketplace_images/"):
    """
    Convenience function to list images from Firebase Storage.
    
    Args:
        prefix (str): Prefix to filter files
    
    Returns:
        list: List of blob names
    """
    manager = get_firebase_manager()
    return manager.list_images(prefix)