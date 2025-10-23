#!/usr/bin/env python3
"""Test script for JWT authentication flow."""
import os
import sys
import json
import requests
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, 'app')

def test_auth_flow():
    """Test the complete authentication flow."""
    base_url = "http://localhost:8000"
    
    print("🔐 Testing JWT Authentication Flow")
    print("=" * 50)
    
    # Test 1: Login with correct credentials
    print("\n1. Testing login with correct credentials...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            token = token_data["access_token"]
            print(f"✅ Login successful! Token: {token[:50]}...")
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
    
    # Test 2: Access protected endpoint with valid token
    print("\n2. Testing protected endpoint with valid token...")
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{base_url}/events", headers=headers)
        if response.status_code == 200:
            print("✅ Protected endpoint accessible with valid token")
        else:
            print(f"❌ Protected endpoint failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Protected endpoint error: {e}")
        return False
    
    # Test 3: Access protected endpoint without token
    print("\n3. Testing protected endpoint without token...")
    try:
        response = requests.get(f"{base_url}/events")
        if response.status_code == 401:
            print("✅ Protected endpoint correctly rejects requests without token")
        else:
            print(f"❌ Expected 401, got: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ No-token test error: {e}")
        return False
    
    # Test 4: Access protected endpoint with invalid token
    print("\n4. Testing protected endpoint with invalid token...")
    invalid_headers = {"Authorization": "Bearer invalid_token"}
    
    try:
        response = requests.get(f"{base_url}/events", headers=invalid_headers)
        if response.status_code == 401:
            print("✅ Protected endpoint correctly rejects invalid token")
        else:
            print(f"❌ Expected 401, got: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Invalid token test error: {e}")
        return False
    
    # Test 5: Access public endpoint without token
    print("\n5. Testing public endpoint without token...")
    try:
        response = requests.get(f"{base_url}/geofence")
        if response.status_code == 200:
            print("✅ Public endpoint accessible without token")
        else:
            print(f"❌ Public endpoint failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Public endpoint error: {e}")
        return False
    
    print("\n🎉 All authentication tests passed!")
    return True

if __name__ == "__main__":
    success = test_auth_flow()
    sys.exit(0 if success else 1)



