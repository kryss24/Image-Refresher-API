from flask import Flask, request, jsonify
import uuid
import requests
from urllib.parse import urlparse
import os
from firebase_utils import upload_image_to_firebase
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Debug route to see all registered routes
@app.route('/debug/routes', methods=['GET'])
def debug_routes():
    """Debug endpoint to see all registered routes."""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'rule': rule.rule,
            'endpoint': rule.endpoint,
            'methods': list(rule.methods)
        })
    return jsonify({'routes': routes})

# Add a simple root route
@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'Facebook Marketplace Image Refresher API is running',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'upload_images': '/upload-images (POST)',
            'debug_routes': '/debug/routes'
        }
    }), 200

def is_valid_url(url):
    """Check if the provided URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def download_image(url, timeout=30):
    """Download image from URL and return binary content."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Check if content is actually an image
        content_type = response.headers.get('content-type', '').lower()
        if not content_type.startswith('image/'):
            raise ValueError(f"URL does not point to an image. Content-Type: {content_type}")
        
        return response.content
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download image from {url}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error downloading image from {url}: {str(e)}")
        raise

def get_file_extension(url, content_type=None):
    """Extract file extension from URL or content type."""
    # Try to get extension from URL first
    parsed_url = urlparse(url)
    path = parsed_url.path
    if '.' in path:
        extension = path.split('.')[-1].lower()
        if extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return extension
    
    # Fallback to content type
    if content_type:
        if 'jpeg' in content_type or 'jpg' in content_type:
            return 'jpg'
        elif 'png' in content_type:
            return 'png'
        elif 'gif' in content_type:
            return 'gif'
        elif 'webp' in content_type:
            return 'webp'
    
    # Default fallback
    return 'jpg'

def process_listing_images(listing):
    """Process all images in a single listing."""
    processed_listing = listing.copy()
    
    # Handle different possible image field names
    image_fields = ['images', 'image_urls', 'photos', 'pictures']
    
    for field in image_fields:
        if field in processed_listing and processed_listing[field]:
            images = processed_listing[field]
            
            # Handle both list of URLs and single URL
            if isinstance(images, str):
                images = [images]
            elif not isinstance(images, list):
                logger.warning(f"Unexpected image field format in listing {processed_listing.get('id', 'unknown')}")
                continue
            
            new_image_urls = []
            
            for i, image_url in enumerate(images):
                if not image_url or not is_valid_url(image_url):
                    logger.warning(f"Invalid URL in listing {processed_listing.get('id', 'unknown')}: {image_url}")
                    continue
                
                try:
                    # Download image
                    logger.info(f"Downloading image {i+1}/{len(images)} from listing {processed_listing.get('id', 'unknown')}")
                    image_data = download_image(image_url)
                    
                    # Generate unique filename
                    listing_id = processed_listing.get('id', str(uuid.uuid4()))
                    extension = get_file_extension(image_url)
                    filename = f"marketplace_images/{listing_id}_{i+1}_{uuid.uuid4().hex[:8]}.{extension}"
                    
                    # Upload to Firebase
                    firebase_url = upload_image_to_firebase(image_data, filename)
                    new_image_urls.append(firebase_url)
                    
                    logger.info(f"Successfully processed image {i+1}/{len(images)} for listing {processed_listing.get('id', 'unknown')}")
                
                except Exception as e:
                    logger.error(f"Failed to process image {image_url} in listing {processed_listing.get('id', 'unknown')}: {str(e)}")
                    # Optionally keep original URL if processing fails
                    # new_image_urls.append(image_url)
                    continue
            
            # Update the field with new URLs
            if new_image_urls:
                if isinstance(processed_listing[field], str):
                    processed_listing[field] = new_image_urls[0] if new_image_urls else processed_listing[field]
                else:
                    processed_listing[field] = new_image_urls
    
    return processed_listing

@app.route('/upload-images', methods=['POST'])
def upload_images():
    """
    Main endpoint to process listings and refresh image URLs.
    Expects JSON array of listing objects.
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        listings = request.json
        
        # Handle None/empty request body
        if listings is None:
            return jsonify({'error': 'Request body cannot be empty'}), 400
        
        if not isinstance(listings, list):
            return jsonify({'error': 'Request body must be an array of listings'}), 400
        
        if not listings:
            return jsonify({'error': 'Listings array cannot be empty'}), 400
        
        logger.info(f"Processing {len(listings)} listings")
        
        # Process each listing
        processed_listings = []
        successful_count = 0
        failed_count = 0
        
        for i, listing in enumerate(listings):
            try:
                logger.info(f"Processing listing {i+1}/{len(listings)}")
                processed_listing = process_listing_images(listing)
                processed_listings.append(processed_listing)
                successful_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process listing {i+1}: {str(e)}")
                # Add original listing to maintain array structure
                processed_listings.append(listing)
                failed_count += 1
        
        # Return results
        response = {
            'success': True,
            'message': f'Processed {len(listings)} listings. {successful_count} successful, {failed_count} failed.',
            'listings': processed_listings,
            'stats': {
                'total_listings': len(listings),
                'successful': successful_count,
                'failed': failed_count
            }
        }
        
        logger.info(f"Completed processing. {successful_count} successful, {failed_count} failed.")
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Unexpected error in upload_images endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error occurred while processing listings'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'Facebook Marketplace Image Refresher API is running'
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Check if Firebase credentials are configured
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS') and not os.path.exists('firebase-credentials.json'):
        logger.warning("Firebase credentials not found. Make sure to set up authentication.")
    
    # Print registered routes for debugging
    print("🔍 Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"   {rule.rule} -> {rule.endpoint} ({list(rule.methods)})")
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)