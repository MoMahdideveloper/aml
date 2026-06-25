import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from tests.test_analytics_api import TestAnalyticsAPI
import json

# Create a simple test runner that mimics what pytest does
class DebugTest(TestAnalyticsAPI):
    def test_trigger_analysis_debug(self):
        # We need to create a mock client and db_setup
        # For now, let's just try to import and see what happens
        print('Import successful')

        # Let's check if we can import the models
        from sqlalchemy_models import AnalysisTemplate, AnalysisReport
        print('Models imported successfully')

        # Check if we can create a template
        from database import db
        from flask import Flask
        from views.analytics import analytics_bp

        print('Creating test app...')
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.register_blueprint(analytics_bp, url_prefix='/api/v2/analysis')

        # Initialize db
        from database import init_db
        init_db(app)

        print('App created successfully')

        with app.test_client() as client:
            with app.app_context():
                # Create tables
                db.create_all()

                # Test creating a template
                template_data = {
                    'name': 'Code Quality Analysis',
                    'description': 'Analyze code quality metrics',
                    'analysis_type': 'code_quality',
                    'configuration': {'check_style': True, 'check_complexity': True},
                    'is_active': True
                }
                print('Creating template...')
                template_response = client.post('/api/v2/analysis/templates', json=template_data)
                print(f'Template creation status: {template_response.status_code}')
                print(f'Template response: {template_response.get_json()}')

                if template_response.status_code == 201:
                    template_data = template_response.get_json()
                    print(f'Template ID: {template_data["id"]}')

                    # Trigger analysis
                    analysis_data = {
                        'template_id': template_data['id'],
                        'name': 'My Code Analysis',
                        'description': 'Analyzing my project code quality'
                    }
                    print('Triggering analysis...')
                    response = client.post('/api/v2/analysis/trigger', json=analysis_data)
                    print(f'Analysis trigger status: {response.status_code}')
                    print(f'Analysis response: {response.get_json()}')

                    # Check if it's a 500 error and get more details
                    if response.status_code == 500:
                        print('ERROR: Got 500 response!')
                        # Let's see what the exception is
                        try:
                            # Force the app to propagate exceptions
                            app.config['PROPAGATE_EXCEPTIONS'] = True
                            response2 = client.post('/api/v2/analysis/trigger', json=analysis_data)
                            print(f'With PROPAGATE_EXCEPTIONS=True: {response2.status_code}')
                        except Exception as e:
                            print(f'Exception caught: {e}')
                            import traceback
                            traceback.print_exc()
                else:
                    print('Failed to create template')

if __name__ == '__main__':
    debug_test = DebugTest()
    debug_test.test_trigger_analysis_debug()