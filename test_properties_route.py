#!/usr/bin/env python3

from app import app
import requests

def test_properties_route():
    with app.test_client() as client:
        print("Testing properties route...")
        response = client.get('/properties')
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            print(f"Redirect Location: {response.headers.get('Location')}")
        
        # Check if response contains properties content or dashboard content
        content = response.get_data(as_text=True)
        if 'Properties - Real Estate CRM' in content:
            print("✓ Properties page loaded correctly")
        elif 'Dashboard - Real Estate CRM' in content:
            print("✗ Dashboard content returned instead of properties")
        else:
            print("? Unknown content returned")
            
        # Check for any error messages
        if 'error' in content.lower():
            print("⚠ Error messages found in response")
            
        print(f"Content length: {len(content)} characters")

if __name__ == "__main__":
    test_properties_route()