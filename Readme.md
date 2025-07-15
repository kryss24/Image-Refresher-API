# Facebook Marketplace Image Refresher API

A Flask-based REST API that solves the common problem of temporary Facebook Marketplace image URLs by downloading images and re-hosting them on Firebase Storage with permanent links.

## 🚀 Features

- **REST API** with Flask framework
- **Batch processing** of multiple listings
- **Automatic image download** from temporary URLs
- **Firebase Storage integration** for permanent hosting
- **Flexible image field support** (images, image_urls, photos, pictures)
- **Error handling** with detailed logging
- **Health check endpoint** for monitoring

## 📋 Prerequisites

- Python 3.8 or higher
- Google Cloud Project with Firebase Storage enabled
- Firebase service account credentials

## 🛠 Installation & Setup

### 1. Clone and Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

### 2. Firebase Setup

#### Option A: Service Account JSON File
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to Project Settings → Service Accounts
4. Click "Generate new private key"
5. Save the JSON file as `firebase-credentials.json` in the project root

#### Option B: Environment Variables
```bash
# Method 1: Path to credentials file
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/firebase-credentials.json"

# Method 2: JSON content directly
export FIREBASE_CREDENTIALS_JSON='{"type": "service_account", "project_id": "your-project-id", ...}'
```

### 3. Configure Firebase Storage Bucket

```bash
# Set your Firebase Storage bucket name
export FIREBASE_STORAGE_BUCKET="your-project-id"
```

**Note:** Use just the project ID, not the full `.appspot.com` URL.

### 4. Firebase Storage Rules

Update your Firebase Storage rules to allow public read access:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /marketplace_images/{allPaths=**} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

## 🚀 Running the Application

### Development Mode
```bash
python app.py
```

### Production Mode
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

The API will be available at `http://localhost:5000`

## 📡 API Endpoints

### POST /upload-images

Processes an array of listings and refreshes their image URLs.

**Request:**
```bash
curl -X POST http://localhost:5000/upload-images \
  -H "Content-Type: application/json" \
  -d @sample_data/input.json
```

**Request Body:**
```json
[
  {
    "id": "listing_001",
    "title": "Sample Item",
    "images": [
      "https://temporary-facebook-url.com/image1.jpg",
      "https://temporary-facebook-url.com/image2.jpg"
    ],
    "price": "$100",
    "description": "Sample description"
  }
]
```

**Response:**
```json
{
  "success": true,
  "message": "Processed 1 listings. 1 successful, 0 failed.",
  "listings": [
    {
      "id": "listing_001",
      "title": "Sample Item",
      "images": [
        "https://storage.googleapis.com/your-bucket/marketplace_images/listing_001_1_abc12345.jpg",
        "https://storage.googleapis.com/your-bucket/marketplace_images/listing_001_2_def67890.jpg"
      ],
      "price": "$100",
      "description": "Sample description"
    }
  ],
  "stats": {
    "total_listings": 1,
    "successful": 1,
    "failed": 0
  }
}
```

### GET /health

Health check endpoint to verify the API is running.

**Response:**
```json
{
  "status": "healthy",
  "message": "Facebook Marketplace Image Refresher API is running"
}
```

## 📁 Project Structure

```
facebook-marketplace-refresher/
├── app.py                    # Main Flask application
├── firebase_utils.py         # Firebase Storage helper functions
├── requirements.txt          # Python dependencies
├── firebase-credentials.json # Firebase service account key (excluded from git)
├── sample_data/
│   ├── input.json           # Sample input data
│   └── output.json          # Sample expected output
└── README.md               # This file
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `FIREBASE_STORAGE_BUCKET` | Firebase Storage bucket name | ✅ | None |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Firebase credentials JSON | ⚠️ | None |
| `FIREBASE_CREDENTIALS_JSON` | Firebase credentials as JSON string | ⚠️ | None |

**Note:** Either `GOOGLE_APPLICATION_CREDENTIALS` or `FIREBASE_CREDENTIALS_JSON` is required.

### Supported Image Fields

The API automatically detects and processes images from these fields:
- `images` (most common)
- `image_urls`
- `photos`
- `pictures`

### Image Processing Features

- **Format Support:** JPG, PNG, GIF, WebP
- **Automatic Extension Detection:** From URL or content type
- **Unique Naming:** Prevents filename conflicts
- **Error Resilience:** Continues processing if individual images fail
- **Public URLs:** All uploaded images are publicly accessible

## 🔍 Testing the API

### Using curl

```bash
# Test with sample data
curl -X POST http://localhost:5000/upload-images \
  -H "Content-Type: application/json" \
  -d @sample_data/input.json

# Health check
curl http://localhost:5000/health
```

### Using Python

```python
import requests
import json

# Load sample data
with open('sample_data/input.json', 'r') as f:
    sample_listings = json.load(f)

# Make request
response = requests.post(
    'http://localhost:5000/upload-images',
    json=sample_listings,
    headers={'Content-Type': 'application/json'}
)

print(response.status_code)
print(response.json())
```

## 📊 Response Format

### Success Response
```json
{
  "success": true,
  "message": "Processed X listings. Y successful, Z failed.",
  "listings": [...],  // Updated listings with new image URLs
  "stats": {
    "total_listings": X,
    "successful": Y,
    "failed": Z
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error description"
}
```

## 🚨 Troubleshooting

### Common Issues

1. **Firebase Authentication Error**
   ```
   Error: Failed to initialize Firebase Storage
   ```
   - Verify your credentials file exists and is valid
   - Check environment variables are set correctly
   - Ensure the service account has Storage Admin permissions

2. **Bucket Not Found**
   ```
   Error: The specified bucket does not exist
   ```
   - Verify `FIREBASE_STORAGE_BUCKET` is set to your project ID
   - Don't include `.appspot.com` in the bucket name
   - Ensure Firebase Storage is enabled in your project

3. **Image Download Failures**
   ```
   Error: Failed to download image from URL
   ```
   - Facebook image URLs expire quickly - process them immediately
   - Check if the URLs are accessible from your server
   - Verify network connectivity and firewall rules

4. **Permission Denied**
   ```
   Error: 403 Forbidden
   ```
   - Ensure your service account has the `Storage Object Admin` role
   - Check Firebase Storage rules allow write access
   - Verify the bucket exists and is accessible

### Debug Mode

Run the application in debug mode for detailed error information:

```bash
export FLASK_DEBUG=1
python app.py
```

### Logging

The application provides detailed logging. Check the console output for:
- Image download progress
- Firebase upload status
- Error details and stack traces
- Processing statistics

## 🔒 Security Considerations

1. **Credentials Storage**
   - Never commit `firebase-credentials.json` to version control
   - Use environment variables in production
   - Rotate service account keys regularly

2. **Access Control**
   - Implement authentication for production use
   - Rate limit requests to prevent abuse
   - Monitor Firebase Storage usage and costs

3. **Input Validation**
   - The API validates URLs and image content
   - Malformed requests are rejected with appropriate errors
   - Only image content types are processed

## 📈 Performance Tips

1. **Batch Processing**
   - Process multiple listings in single requests
   - Optimal batch size: 10-50 listings

2. **Error Handling**
   - Failed images don't stop processing of other images
   - Original URLs are preserved if processing fails

3. **Firebase Optimization**
   - Images are stored with organized folder structure
   - Public access is set automatically
   - Unique filenames prevent conflicts

## 📝 API Usage Examples

### Single Listing
```json
[
  {
    "id": "single_item",
    "title": "Test Item",
    "images": ["https://facebook-temp-url.com/image.jpg"]
  }
]
```

### Multiple Image Fields
```json
[
  {
    "id": "multi_field",
    "images": ["url1.jpg"],
    "photos": ["url2.jpg"],
    "image_urls": ["url3.jpg"]
  }
]
```

### Mixed Data Types
```json
[
  {
    "id": "mixed_item",
    "images": "single-url.jpg",  // String (converted to array)
    "custom_field": "preserved_data"
  }
]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review Firebase Console for storage issues
3. Check application logs for detailed error messages
4. Open an issue on the project repository

---
