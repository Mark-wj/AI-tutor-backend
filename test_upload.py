#!/usr/bin/env python3
"""
Test script for document upload endpoint
Run this after starting your FastAPI server
"""

import requests
import json
import tempfile
import os

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_CONTENT = """
Machine Learning: An Introduction

Machine learning is a subset of artificial intelligence (AI) that focuses on the development of algorithms and statistical models that enable computer systems to improve their performance on a specific task through experience, without being explicitly programmed for every scenario.

Key Concepts:
1. Supervised Learning - Learning with labeled examples
2. Unsupervised Learning - Finding patterns in unlabeled data
3. Reinforcement Learning - Learning through trial and error

Applications:
- Image recognition
- Natural language processing
- Recommendation systems
- Autonomous vehicles

Machine learning has revolutionized many industries and continues to be one of the most important technological advances of our time.
"""

def test_health():
    """Test if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server is healthy")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False

def test_upload():
    """Test document upload"""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(TEST_CONTENT)
            temp_file_path = f.name

        # Upload the file
        with open(temp_file_path, 'rb') as f:
            files = {'file': ('test_document.txt', f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/api/documents/upload", files=files)
        
        # Clean up
        os.unlink(temp_file_path)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload successful!")
            print(f"   Document ID: {data.get('id')}")
            print(f"   Filename: {data.get('filename')}")
            print(f"   Status: {data.get('status')}")
            return data.get('id')
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def test_get_documents():
    """Test getting all documents"""
    try:
        response = requests.get(f"{BASE_URL}/api/documents/")
        if response.status_code == 200:
            documents = response.json()
            print(f"✅ Retrieved {len(documents)} documents")
            for doc in documents[:3]:  # Show first 3
                print(f"   - {doc.get('filename')} (ID: {doc.get('id')})")
            return True
        else:
            print(f"❌ Get documents failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get documents error: {e}")
        return False

def test_get_document(doc_id):
    """Test getting a specific document"""
    if not doc_id:
        print("⏭️  Skipping document detail test (no document ID)")
        return False
        
    try:
        response = requests.get(f"{BASE_URL}/api/documents/{doc_id}")
        if response.status_code == 200:
            document = response.json()
            print(f"✅ Retrieved document details for ID {doc_id}")
            print(f"   Filename: {document.get('filename')}")
            print(f"   Content length: {len(document.get('content', ''))}")
            return True
        else:
            print(f"❌ Get document failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get document error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing AI Tutoring Backend API")
    print("=" * 40)
    
    # Test server health
    if not test_health():
        print("\n❌ Server is not running. Start it with:")
        print("   uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        return
    
    print()
    
    # Test document upload
    print("🔄 Testing document upload...")
    doc_id = test_upload()
    
    print()
    
    # Test getting all documents
    print("🔄 Testing get all documents...")
    test_get_documents()
    
    print()
    
    # Test getting specific document
    print("🔄 Testing get specific document...")
    test_get_document(doc_id)
    
    print()
    print("🎉 Testing complete!")
    print(f"📚 Visit {BASE_URL}/docs to see the full API documentation")

if __name__ == "__main__":
    main()