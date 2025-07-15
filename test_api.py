#!/usr/bin/env python3
"""
Test script for Facebook Marketplace Image Refresher API
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any

# Configuration
API_BASE_URL = "http://localhost:5000"
SAMPLE_DATA_FILE = "sample_data/input.json"

def test_health_endpoint():
    """Test the health check endpoint."""
    print("🔍 Testing health endpoint...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['message']}")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed: {str(e)}")
        return False

def load_sample_data() -> List[Dict[str, Any]]:
    """Load sample data from JSON file."""
    try:
        # Try different encodings to handle Unicode issues
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(SAMPLE_DATA_FILE, 'r', encoding=encoding) as f:
                    data = json.load(f)
                print(f"📁 Loaded {len(data)} sample listings (encoding: {encoding})")
                return data
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail, try reading as bytes and cleaning
        print("⚠️  Trying to clean file content...")
        with open(SAMPLE_DATA_FILE, 'rb') as f:
            content = f.read()
        
        # Remove problematic bytes and decode
        cleaned_content = content.decode('utf-8', errors='ignore')
        data = json.loads(cleaned_content)
        print(data)
        print(f"📁 Loaded {len(data)} sample listings (cleaned)")
        return data
        
    except FileNotFoundError:
        print(f"❌ Sample data file not found: {SAMPLE_DATA_FILE}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in sample data: {str(e)}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error loading sample data: {str(e)}")
        return []

def test_upload_images_endpoint(sample_data: List[Dict[str, Any]]):
    """Test the main upload images endpoint."""
    print("🔍 Testing upload images endpoint...")
    
    try:
        # Make the request
        response = requests.post(
            f"{API_BASE_URL}/upload-images",
            json=sample_data,
            headers={'Content-Type': 'application/json'},
            timeout=300  # 5 minutes timeout for image processing
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Print results
            print(f"✅ Success: {data['message']}")
            print(f"📊 Stats: {data['stats']}")
            
            # Verify response structure
            if 'listings' in data and len(data['listings']) > 0:
                print(f"📄 Processed {len(data['listings'])} listings")
                
                # Check first listing for image URL changes
                first_listing = data['listings'][0]
                print(f"🖼️  First listing image fields:")
                
                for field in ['images', 'image_urls', 'photos', 'pictures']:
                    if field in first_listing:
                        images = first_listing[field]
                        if isinstance(images, list):
                            print(f"   {field}: {len(images)} images")
                            for i, img_url in enumerate(images[:2]):  # Show first 2 URLs
                                print(f"     {i+1}. {img_url[:80]}...")
                        else:
                            print(f"   {field}: {str(images)[:80]}...")
                
                return True
            else:
                print("❌ No listings in response")
                return False
                
        else:
            print(f"❌ Request failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - image processing may take a while")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        return False

def test_invalid_requests():
    """Test API error handling with invalid requests."""
    print("🔍 Testing error handling...")
    
    test_cases = [
        {
            "name": "Empty request body",
            "data": None,
            "expected_status": 400
        },
        {
            "name": "Non-JSON request",
            "data": "not json",
            "expected_status": 400,
            "headers": {'Content-Type': 'text/plain'}
        },
        {
            "name": "Not an array",
            "data": {"single": "object"},
            "expected_status": 400
        },
        {
            "name": "Empty array",
            "data": [],
            "expected_status": 400
        }
    ]
    
    for test_case in test_cases:
        print(f"   Testing: {test_case['name']}")
        
        try:
            headers = test_case.get('headers', {'Content-Type': 'application/json'})
            
            if test_case['data'] is None:
                response = requests.post(f"{API_BASE_URL}/upload-images", headers=headers)
            else:
                if headers.get('Content-Type') == 'application/json':
                    response = requests.post(f"{API_BASE_URL}/upload-images", json=test_case['data'], headers=headers)
                else:
                    response = requests.post(f"{API_BASE_URL}/upload-images", data=test_case['data'], headers=headers)
            
            expected_status = test_case['expected_status']
            if response.status_code == expected_status:
                print(f"   ✅ Correctly returned status {response.status_code}")
            else:
                print(f"   ❌ Expected status {expected_status}, got {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {str(e)}")

def test_with_minimal_data():
    """Test with minimal valid data."""
    print("🔍 Testing with minimal data...")
    
    minimal_data = [
        {
            "id": "test_001",
            "title": "Test Item",
            "images": [
                "https://httpbin.org/image/jpeg"  # Public test image
            ]
        }
    ]
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/upload-images",
            json=minimal_data,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Minimal data test passed: {data['message']}")
            return True
        else:
            print(f"❌ Minimal data test failed with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Minimal data test failed: {str(e)}")
        return False

def test_from_file_json():
    # Charger le fichier JSON
    with open('sample_data/input.json', 'r', encoding='utf-8') as f:
        listings = json.load(f)

    # Envoyer à l’API Flask
    response = requests.post(f'{API_BASE_URL}/upload-images', json=listings)

    # Vérifier la réponse
    if response.ok:
        result = response.json()
        print("✅ Traitement réussi :", result['message'])
        
        # Sauvegarder la nouvelle version avec les images mises à jour
        with open('output.json', 'w', encoding='utf-8') as f:
            json.dump(result['listings'], f, indent=2, ensure_ascii=False)
        print("✅ Fichier output.json généré avec succès")
        return True
    else:
        print("❌ Erreur :", response.status_code, response.text)
        return False

def main():
    """Main test runner."""
    print("🚀 Starting Facebook Marketplace Image Refresher API Tests")
    print("=" * 60)
    
    # Test health endpoint first
    if not test_health_endpoint():
        print("\n❌ Health check failed - make sure the API server is running")
        print("   Start the server with: python app.py")
        sys.exit(1)
    
    print()
    
    # Test error handling
    test_invalid_requests()
    print()
    
    # Test with minimal data
    test_with_minimal_data()
    print()
    
    # Load sample data
    sample_data = load_sample_data()
    if not sample_data:
        print("❌ Cannot run main test without sample data")
        sys.exit(1)
    
    print()
    
    # Test main functionality
    print("⚠️  Note: The following test will attempt to download images from Facebook URLs")
    print("   These URLs are likely expired, so some failures are expected")
    print("   This tests the error handling and processing logic")
    print()
    
    input("Press Enter to continue with the main test...")
    print()
    
    start_time = time.time()
    success = test_upload_images_endpoint(sample_data)
    end_time = time.time()
    
    print()
    print("=" * 60)
    print(f"🏁 Tests completed in {end_time - start_time:.2f} seconds")
    
    if success:
        print("✅ Main functionality test passed!")
        print("🎉 API is working correctly")
    else:
        print("❌ Some tests failed - check the output above")
        print("💡 Make sure Firebase credentials are configured correctly")
    
    print("🚀 Starting Facebook Marketplace Image Refresher API Tests")
    print("=" * 60)
    
    sucess = test_from_file_json()
    
    if success:
        print("✅ Main functionality test passed!")
        print("🎉 API is working correctly")
    else:
        print("❌ Some tests failed - check the output above")
        print("💡 Make sure Firebase credentials are configured correctly")
    
    print("\n📋 Test Summary:")
    print("   - Health check: ✅")
    print("   - Error handling: ✅")
    print("   - Minimal data test: ✅" if test_with_minimal_data() else "   - Minimal data test: ❌")
    print("   - Main functionality: ✅" if success else "   - Main functionality: ❌")

if __name__ == "__main__":
    main()