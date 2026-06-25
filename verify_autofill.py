
import os
import sys
import unittest
import json

# Add current directory to path
sys.path.append(os.getcwd())

from app import create_app
from database import db

class TestAIAutofill(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        with self.app.app_context():
            # Ensure tables are created (in-memory sqlite)
            db.create_all()

    def test_parse_property_route(self):
        """Test the property parsing endpoint"""
        test_text = "Beautiful 3-bedroom apartment in North Tehran, 150sqm, built 2022, price $500,000"
        response = self.client.post('/api/ai/parse/property', 
                                    data=json.dumps({"text": test_text}),
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        print("\nProperty Parsing Response:")
        print(json.dumps(data, indent=2))
        
        self.assertIn('entity', data)
        self.assertEqual(data['entity'], 'property')
        self.assertIn('data', data)
        self.assertIn('confidence', data)

    def test_parse_customer_route(self):
        """Test the customer parsing endpoint"""
        test_text = "John Doe, email john@example.com, looking for a 2-bedroom rental in West Tehran up to $1000/mo"
        response = self.client.post('/api/ai/parse/customer', 
                                    data=json.dumps({"text": test_text}),
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        print("\nCustomer Parsing Response:")
        print(json.dumps(data, indent=2))
        
        self.assertIn('entity', data)
        self.assertEqual(data['entity'], 'customer')
        self.assertIn('data', data)
        self.assertIn('confidence', data)

    def test_parse_no_text(self):
        """Test the endpoint with no text"""
        response = self.client.post('/api/ai/parse/property', 
                                    data=json.dumps({}),
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
