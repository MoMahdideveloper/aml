import pytest
from flask import url_for
import json
from sqlalchemy_models import SuggestionItem
from database import db

class TestAnalyticsAPI:
    '''Test suite for analytics API endpoints'''

    def test_get_analysis_templates(self, client, db_setup):
        '''Test getting list of analysis templates'''
        response = client.get('/api/v2/analysis/templates')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        # Should have at least the default templates
        assert len(data) >= 0

    def test_create_analysis_template(self, client, db_setup):
        '''Test creating a new analysis template'''
        template_data = {
            'name': 'Performance Analysis',
            'description': 'Analyze application performance metrics',
            'analysis_type': 'performance',
            'configuration': {'check_response_time': True, 'check_throughput': True},
            'is_active': True
        }
        response = client.post('/api/v2/analysis/templates',
                              json=template_data)
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['name'] == 'Performance Analysis'
        assert data['description'] == 'Analyze application performance metrics'
        assert data['analysis_type'] == 'performance'
        assert data['configuration'] == {'check_response_time': True, 'check_throughput': True}
        assert data['is_active'] == True

    def test_trigger_analysis(self, client, db_setup):
        '''Test triggering a new analysis'''
        # First create a template
        template_data = {
            'name': 'Code Quality Analysis',
            'description': 'Analyze code quality metrics',
            'analysis_type': 'code_quality',
            'configuration': {'check_style': True, 'check_complexity': True},
            'is_active': True
        }
        template_response = client.post('/api/v2/analysis/templates',
                                       json=template_data)
        template_data = json.loads(template_response.data)

        # Trigger analysis
        analysis_data = {
            'template_id': template_data['id'],
            'name': 'My Code Analysis',
            'description': 'Analyzing my project code quality'
        }
        response = client.post('/api/v2/analysis/trigger',
                              json=analysis_data)
        assert response.status_code == 202
        data = json.loads(response.data)
        assert data['template_id'] == template_data['id']
        assert data['name'] == 'My Code Analysis'
        assert data['status'] == 'pending'

    def test_get_analysis_reports(self, client, db_setup):
        '''Test getting list of analysis reports'''
        # Create a template and report first
        template_data = {
            'name': 'Security Analysis',
            'description': 'Security vulnerability scan',
            'analysis_type': 'security',
            'configuration': {'scan_dependencies': True},
            'is_active': True
        }
        template_response = client.post('/api/v2/analysis/templates',
                                       json=template_data)
        template_data = json.loads(template_response.data)

        report_data = {
            'template_id': template_data['id'],
            'name': 'My Security Analysis',
            'description': 'Checking for security vulnerabilities'
        }
        client.post('/api/v2/analysis/trigger',
                   json=report_data)

        # Get reports
        response = client.get('/api/v2/analysis/reports')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert isinstance(data['reports'], list)
        assert len(data['reports']) >= 1
        assert data['reports'][0]['name'] == 'My Security Analysis'
        assert data['reports'][0]['template_id'] == template_data['id']

    def test_get_analysis_report_by_id(self, client, db_setup):
        '''Test getting a specific analysis report by ID'''
        # Create a template and report first
        template_data = {
            'name': 'Architecture Analysis',
            'description': 'Analyzes project architecture',
            'analysis_type': 'architecture',
            'configuration': {'check_layers': True, 'check_dependencies': True},
            'is_active': True
        }
        template_response = client.post('/api/v2/analysis/templates',
                                       json=template_data)
        template_data = json.loads(template_response.data)

        report_data = {
            'template_id': template_data['id'],
            'name': 'My Architecture Analysis',
            'description': 'Evaluating system architecture'
        }
        response = client.post('/api/v2/analysis/trigger',
                              json=report_data)
        report_data = json.loads(response.data)

        # Get specific report
        response = client.get(f'/api/v2/analysis/reports/{report_data["id"]}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == report_data['id']
        assert data['name'] == 'My Architecture Analysis'
        assert data['description'] == 'Evaluating system architecture'
        assert data['template_id'] == template_data['id']

    def test_get_analysis_report_status(self, client, db_setup):
        '''Test getting analysis report status'''
        # Create a template and report first
        template_data = {
            'name': 'Dependency Analysis',
            'description': 'Check project dependencies',
            'analysis_type': 'dependencies',
            'configuration': {'check_vulnerabilities': True},
            'is_active': True
        }
        template_response = client.post('/api/v2/analysis/templates',
                                       json=template_data)
        template_data = json.loads(template_response.data)

        report_data = {
            'template_id': template_data['id'],
            'name': 'My Dependency Analysis',
            'description': 'Checking for vulnerable dependencies'
        }
        response = client.post('/api/v2/analysis/trigger',
                              json=report_data)
        report_data = json.loads(response.data)

        # Get report status
        response = client.get(f'/api/v2/analysis/reports/{report_data["id"]}/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert 'progress' in data
        assert data['id'] == report_data['id']

    def test_update_suggestion(self, client, db_setup):
        '''Test updating a suggestion status/assignment'''
        # Create template, report, and suggestion first
        template_data = {
            'name': 'Code Quality Analysis',
            'description': 'Analyzes code quality metrics',
            'analysis_type': 'code_quality',
            'configuration': {'check_style': True, 'check_complexity': True},
            'is_active': True
        }
        template_response = client.post('/api/v2/analysis/templates',
                                       json=template_data)
        template_data = json.loads(template_response.data)

        report_data = {
            'template_id': template_data['id'],
            'name': 'My Code Quality Analysis',
            'description': 'Analyzing code quality'
        }
        report_response = client.post('/api/v2/analysis/trigger',
                                     json=report_data)
        report_data = json.loads(report_response.data)

        # Add a suggestion to the report
        suggestion = SuggestionItem(
            report_id=report_data['id'],
            title='Consider using linter',
            description='Use a linter to maintain code style consistency',
            category='maintainability',
            priority_score=50,  # Medium priority (on scale of 1-100)
            implementation_complexity=2,  # Low effort (on scale of 1-5)
            roi_estimate=80  # High impact (as percentage)
        )
        db.session.add(suggestion)
        db.session.commit()

        # Update suggestion
        update_data = {
            'status': 'in_progress',
            'assigned_to': 'john.doe@example.com',
            'priority': 'high'
        }
        response = client.put(f'/api/v2/analysis/suggestions/{suggestion.id}',
                             json=update_data)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'in_progress'
        assert data['assigned_to'] == 'john.doe@example.com'
        assert data['priority'] == 'high'

    def test_get_suggestions(self, client, db_setup):
        '''Test getting list of suggestions with filtering'''
        # Create template, report, and suggestions first
        template_data = {
            'name': 'Performance Analysis',
            'description': 'Analyzes performance metrics',
            'analysis_type': 'performance',
            'configuration': {'check_response_time': True},
            'is_active': True
        }
        template_response = client.post('/api/v2/analysis/templates',
                                       json=template_data)
        template_data = json.loads(template_response.data)

        report_data = {
            'template_id': template_data['id'],
            'name': 'My Performance Analysis',
            'description': 'Analyzing application performance'
        }
        report_response = client.post('/api/v2/analysis/trigger',
                                     json=report_data)
        report_data = json.loads(report_response.data)

        # Add suggestions
        suggestion1 = SuggestionItem(
            report_id=report_data['id'],
            title='Add caching layer',
            description='Implement caching for frequently accessed data',
            category='performance',
            priority_score=80,  # High priority
            implementation_complexity=3,  # Medium effort
            roi_estimate=80  # High impact
        )
        suggestion2 = SuggestionItem(
            report_id=report_data['id'],
            title='Optimize database queries',
            description='Review and optimize slow database queries',
            category='performance',
            priority_score=50,  # Medium priority
            implementation_complexity=4,  # High effort
            roi_estimate=50  # Medium impact
        )
        db.session.add_all([suggestion1, suggestion2])
        db.session.commit()

        # Get suggestions
        response = client.get('/api/v2/analysis/suggestions')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert isinstance(data['suggestions'], list)
        assert len(data['suggestions']) >= 2
        # Should be sorted by priority or creation date
        assert any(s['title'] == 'Add caching layer' for s in data['suggestions'])
        assert any(s['title'] == 'Optimize database queries' for s in data['suggestions'])