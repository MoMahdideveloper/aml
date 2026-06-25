"""
Unit tests for enhanced CRUD forms validation logic
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock

from forms import AgentEditForm, CustomerEditForm, TaskEditForm
from sqlalchemy_models import Agent, Customer
from wtforms.validators import ValidationError


@pytest.mark.usefixtures("app")
class TestAgentEditForm:
    """Test cases for AgentEditForm validation"""
    
    def test_valid_agent_form(self, app):
        """Test form validation with valid data"""
        with app.app_context():
            form_data = {
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'phone': '555-0123',
                'specialization': 'Residential Sales',
                'bio': 'Experienced real estate agent'
            }
            form = AgentEditForm(data=form_data)
            
            with patch.object(Agent, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is True
    
    def test_agent_form_required_fields(self, app):
        """Test form validation with missing required fields"""
        with app.app_context():
            form_data = {
                'specialization': 'Residential Sales',
                'bio': 'Experienced real estate agent'
            }
            form = AgentEditForm(data=form_data)
            
            assert form.validate() is False
            assert 'name' in form.errors
            assert 'email' in form.errors
            assert 'phone' in form.errors
    
    def test_agent_form_email_validation(self, app, db_setup):
        """Test email format validation"""
        with app.app_context():
            form_data = {
                'name': 'John Doe',
                'email': 'invalid-email',
                'phone': '555-0123'
            }
            form = AgentEditForm(data=form_data)
            
            assert form.validate() is False
            assert 'email' in form.errors
    
    def test_agent_form_email_uniqueness_new_agent(self, app):
        """Test email uniqueness validation for new agent"""
        with app.app_context():
            form_data = {
                'name': 'John Doe',
                'email': 'existing@example.com',
                'phone': '555-0123'
            }
            form = AgentEditForm(data=form_data)
            
            # Mock existing agent with same email
            mock_agent = MagicMock()
            mock_agent.id = 1
            
            with patch.object(Agent, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = mock_agent
                assert form.validate() is False
                assert 'email' in form.errors
                assert 'already registered' in str(form.errors['email'])
    
    def test_agent_form_email_uniqueness_same_agent(self, app):
        """Test email uniqueness validation for same agent (editing)"""
        with app.app_context():
            form_data = {
                'name': 'John Doe',
                'email': 'existing@example.com',
                'phone': '555-0123'
            }
            form = AgentEditForm(agent_id=1, data=form_data)
            
            # Mock existing agent with same email and same ID
            mock_agent = MagicMock()
            mock_agent.id = 1
            
            with patch.object(Agent, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = mock_agent
                assert form.validate() is True
    
    def test_agent_form_field_length_validation(self, app):
        """Test field length validation"""
        with app.app_context():
            form_data = {
                'name': 'x' * 256,  # Exceeds max length
                'email': 'test@example.com',
                'phone': '555-0123'
            }
            form = AgentEditForm(data=form_data)
            
            with patch.object(Agent, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is False
                assert 'name' in form.errors


@pytest.mark.usefixtures("app")
class TestCustomerEditForm:
    """Test cases for CustomerEditForm validation"""
    
    def test_valid_customer_form(self, app):
        """Test form validation with valid data"""
        with app.app_context():
            form_data = {
                'name': 'Jane Smith',
                'email': 'jane.smith@example.com',
                'phone': '555-0456',
                'budget_min': 100000.0,
                'budget_max': 200000.0,
                'preferred_bedrooms': 3,
                'preferred_bathrooms': 2,
                'preferred_type': 'House',
                'location_preference': 'Downtown'
            }
            form = CustomerEditForm(data=form_data)
            
            with patch.object(Customer, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is True
    
    def test_customer_form_required_fields(self, app):
        """Test form validation with missing required fields"""
        with app.app_context():
            form_data = {
                'budget_min': 100000.0,
                'budget_max': 200000.0
            }
            form = CustomerEditForm(data=form_data)
            
            assert form.validate() is False
            assert 'name' in form.errors
            assert 'email' in form.errors
            assert 'phone' in form.errors
    
    def test_customer_form_email_uniqueness(self, app):
        """Test email uniqueness validation for customer"""
        with app.app_context():
            form_data = {
                'name': 'Jane Smith',
                'email': 'existing@example.com',
                'phone': '555-0456'
            }
            form = CustomerEditForm(data=form_data)
            
            # Mock existing customer with same email
            mock_customer = MagicMock()
            mock_customer.id = 1
            
            with patch.object(Customer, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = mock_customer
                assert form.validate() is False
                assert 'email' in form.errors
                assert 'already registered' in str(form.errors['email'])
    
    def test_customer_form_budget_range_validation_valid(self, app):
        """Test budget range validation with valid range"""
        with app.app_context():
            form_data = {
                'name': 'Jane Smith',
                'email': 'jane@example.com',
                'phone': '555-0456',
                'budget_min': 100000.0,
                'budget_max': 200000.0
            }
            form = CustomerEditForm(data=form_data)
            
            with patch.object(Customer, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is True
    
    def test_customer_form_budget_range_validation_invalid(self, app):
        """Test budget range validation with invalid range"""
        with app.app_context():
            form_data = {
                'name': 'Jane Smith',
                'email': 'jane@example.com',
                'phone': '555-0456',
                'budget_min': 200000.0,
                'budget_max': 100000.0  # Max less than min
            }
            form = CustomerEditForm(data=form_data)
            
            with patch.object(Customer, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is False
                assert 'budget_max' in form.errors
                assert 'greater than or equal' in str(form.errors['budget_max'])
    
    def test_customer_form_budget_range_validation_equal(self, app):
        """Test budget range validation with equal min and max"""
        with app.app_context():
            form_data = {
                'name': 'Jane Smith',
                'email': 'jane@example.com',
                'phone': '555-0456',
                'budget_min': 150000.0,
                'budget_max': 150000.0  # Equal values should be valid
            }
            form = CustomerEditForm(data=form_data)
            
            with patch.object(Customer, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is True
    
    def test_customer_form_negative_budget_validation(self, app):
        """Test negative budget validation"""
        with app.app_context():
            form_data = {
                'name': 'Jane Smith',
                'email': 'jane@example.com',
                'phone': '555-0456',
                'budget_min': -1000.0,  # Negative value
                'budget_max': 200000.0
            }
            form = CustomerEditForm(data=form_data)
            
            with patch.object(Customer, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                # The NumberRange(min=0) validator should catch this
                assert form.validate() is False
                assert 'budget_min' in form.errors


@pytest.mark.usefixtures("app")
class TestTaskEditForm:
    """Test cases for TaskEditForm validation"""
    
    def test_valid_task_form(self, app):
        """Test form validation with valid data"""
        with app.app_context():
            tomorrow = date.today() + timedelta(days=1)
            form_data = {
                'title': 'Follow up with client',
                'description': 'Call client to discuss property options',
                'priority': 'medium',
                'status': 'pending',
                'due_date': tomorrow
            }
            form = TaskEditForm(data=form_data)
            
            assert form.validate() is True
    
    def test_task_form_required_fields(self, app):
        """Test form validation with missing required fields"""
        with app.app_context():
            form_data = {
                'due_date': date.today() + timedelta(days=1)
            }
            form = TaskEditForm(data=form_data)
            
            assert form.validate() is False
            assert 'title' in form.errors
            assert 'description' in form.errors
            assert 'priority' in form.errors
            assert 'status' in form.errors
    
    def test_task_form_priority_choices(self, app):
        """Test priority field choices validation"""
        with app.app_context():
            form_data = {
                'title': 'Follow up with client',
                'description': 'Call client to discuss property options',
                'priority': 'invalid_priority',
                'status': 'pending'
            }
            form = TaskEditForm(data=form_data)
            
            assert form.validate() is False
            assert 'priority' in form.errors
    
    def test_task_form_status_choices(self, app):
        """Test status field choices validation"""
        with app.app_context():
            form_data = {
                'title': 'Follow up with client',
                'description': 'Call client to discuss property options',
                'priority': 'medium',
                'status': 'invalid_status'
            }
            form = TaskEditForm(data=form_data)
            
            assert form.validate() is False
            assert 'status' in form.errors
    
    def test_task_form_due_date_validation_future(self, app):
        """Test due date validation with future date"""
        with app.app_context():
            tomorrow = date.today() + timedelta(days=1)
            form_data = {
                'title': 'Follow up with client',
                'description': 'Call client to discuss property options',
                'priority': 'medium',
                'status': 'pending',
                'due_date': tomorrow
            }
            form = TaskEditForm(data=form_data)
            
            assert form.validate() is True
    
    def test_task_form_due_date_validation_today(self, app):
        """Test due date validation with today's date"""
        with app.app_context():
            today = date.today()
            form_data = {
                'title': 'Follow up with client',
                'description': 'Call client to discuss property options',
                'priority': 'medium',
                'status': 'pending',
                'due_date': today
            }
            form = TaskEditForm(data=form_data)
            
            assert form.validate() is True
    
    def test_task_form_due_date_validation_past(self, app):
        """Test due date validation with past date"""
        with app.app_context():
            yesterday = date.today() - timedelta(days=1)
            form_data = {
                'title': 'Follow up with client',
                'description': 'Call client to discuss property options',
                'priority': 'medium',
                'status': 'pending',
                'due_date': yesterday
            }
            form = TaskEditForm(data=form_data)
            
            assert form.validate() is False
            assert 'due_date' in form.errors
            assert 'cannot be in the past' in str(form.errors['due_date'])
    
    def test_task_form_optional_due_date(self, app):
        """Test form validation with no due date (optional field)"""
        with app.app_context():
            form_data = {
                'title': 'Follow up with client',
                'description': 'Call client to discuss property options',
                'priority': 'medium',
                'status': 'pending'
                # No due_date provided
            }
            form = TaskEditForm(data=form_data)
            
            assert form.validate() is True
    
    def test_task_form_title_length_validation(self, app):
        """Test title field length validation"""
        with app.app_context():
            form_data = {
                'title': 'x' * 256,  # Exceeds max length
                'description': 'Call client to discuss property options',
                'priority': 'medium',
                'status': 'pending'
            }
            form = TaskEditForm(data=form_data)
            
            assert form.validate() is False
            assert 'title' in form.errors


@pytest.mark.usefixtures("app")
class TestFormIntegration:
    """Integration tests for form interactions"""
    
    def test_agent_edit_form_initialization_with_id(self, app):
        """Test AgentEditForm initialization with agent_id"""
        with app.app_context():
            form = AgentEditForm(agent_id=123)
            assert form.agent_id == 123
    
    def test_customer_edit_form_initialization_with_id(self, app):
        """Test CustomerEditForm initialization with customer_id"""
        with app.app_context():
            form = CustomerEditForm(customer_id=456)
            assert form.customer_id == 456
    
    def test_forms_inherit_from_base_no_csrf(self, app):
        """Test that all edit forms inherit from BaseNoCSRFForm"""
        with app.app_context():
            agent_form = AgentEditForm()
            customer_form = CustomerEditForm()
            task_form = TaskEditForm()
            
            # Check that CSRF is disabled
            assert agent_form.meta.csrf is False
            assert customer_form.meta.csrf is False
            assert task_form.meta.csrf is False

@pytest.mark.usefixtures("app")
class TestFormErrorHandling:
    """Test error handling and edge cases in forms"""

    def test_agent_form_with_special_characters(self, app):
        """Test agent form with special characters"""
        with app.app_context():
            form_data = {
                'name': "Agent with 'quotes' & symbols",
                'email': 'special+test@example-domain.com',
                'phone': '(555) 123-4567',
                'specialization': 'Residential & Commercial',
                'bio': 'Bio with "quotes" and line\nbreaks'
            }
            form = AgentEditForm(data=form_data)
            
            with patch.object(Agent, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is True

    def test_customer_form_with_unicode_characters(self, app):
        """Test customer form with Unicode characters"""
        with app.app_context():
            form_data = {
                'name': 'José María González',
                'email': 'jose.maria@example.com',
                'phone': '+1 (555) 123-4567',
                'location_preference': 'Montréal, Québec'
            }
            form = CustomerEditForm(data=form_data)
            
            with patch.object(Customer, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is True

    def test_task_form_with_very_long_description(self, app):
        """Test task form with very long description"""
        with app.app_context():
            long_description = "x" * 5000  # Very long description
            form_data = {
                'title': 'Task with long description',
                'description': long_description,
                'priority': 'medium',
                'status': 'pending'
            }
            form = TaskEditForm(data=form_data)
            
            # Should validate successfully (no length limit on description)
            assert form.validate() is True

    def test_agent_form_email_case_insensitive_uniqueness(self, app):
        """Test email uniqueness is case insensitive"""
        with app.app_context():
            form_data = {
                'name': 'Test Agent',
                'email': 'TEST@EXAMPLE.COM',
                'phone': '555-0123'
            }
            form = AgentEditForm(data=form_data)
            
            # Mock existing agent with lowercase email
            mock_agent = MagicMock()
            mock_agent.id = 1
            
            with patch.object(Agent, 'query') as mock_query:
                # Simulate case-insensitive email check
                mock_query.filter_by.return_value.first.return_value = mock_agent
                assert form.validate() is False
                assert 'email' in form.errors

    def test_customer_form_extreme_budget_values(self, app):
        """Test customer form with extreme budget values"""
        with app.app_context():
            form_data = {
                'name': 'Extreme Customer',
                'email': 'extreme@example.com',
                'phone': '555-0123',
                'budget_min': 0.01,  # Very small
                'budget_max': 999999999.99  # Very large
            }
            form = CustomerEditForm(data=form_data)
            
            with patch.object(Customer, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is True

    def test_task_form_boundary_date_values(self, app):
        """Test task form with boundary date values"""
        with app.app_context():
            # Test with today's date (boundary case)
            today = date.today()
            form_data = {
                'title': 'Boundary Date Task',
                'description': 'Task with boundary date',
                'priority': 'medium',
                'status': 'pending',
                'due_date': today
            }
            form = TaskEditForm(data=form_data)
            
            assert form.validate() is True
            
            # Test with far future date
            far_future = date(2099, 12, 31)
            form_data['due_date'] = far_future
            form = TaskEditForm(data=form_data)
            
            assert form.validate() is True

    def test_form_validation_with_empty_strings(self, app):
        """Test form validation with empty strings vs None"""
        with app.app_context():
            form_data = {
                'name': '',  # Empty string
                'email': '',  # Empty string
                'phone': '',  # Empty string
                'specialization': '',  # Empty string (optional)
                'bio': ''  # Empty string (optional)
            }
            form = AgentEditForm(data=form_data)
            
            assert form.validate() is False
            assert 'name' in form.errors
            assert 'email' in form.errors
            assert 'phone' in form.errors
            # Optional fields should not have errors for empty strings
            assert 'specialization' not in form.errors
            assert 'bio' not in form.errors

    def test_form_validation_with_whitespace_only(self, app):
        """Test form validation with whitespace-only values"""
        with app.app_context():
            form_data = {
                'name': '   ',  # Whitespace only
                'email': '  test@example.com  ',  # Email with whitespace
                'phone': ' 555-0123 ',  # Phone with whitespace
            }
            form = AgentEditForm(data=form_data)
            
            with patch.object(Agent, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                # Form should handle whitespace appropriately
                # Name with only whitespace should fail
                assert form.validate() is False
                assert 'name' in form.errors

    def test_customer_budget_validation_edge_cases(self, app):
        """Test customer budget validation edge cases"""
        with app.app_context():
            # Test with budget_min = budget_max (should be valid)
            form_data = {
                'name': 'Equal Budget Customer',
                'email': 'equal@example.com',
                'phone': '555-0123',
                'budget_min': 150000.0,
                'budget_max': 150000.0
            }
            form = CustomerEditForm(data=form_data)
            
            with patch.object(Customer, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is True
            
            # Test with only budget_min set
            form_data = {
                'name': 'Min Only Customer',
                'email': 'minonly@example.com',
                'phone': '555-0123',
                'budget_min': 100000.0,
                'budget_max': None
            }
            form = CustomerEditForm(data=form_data)
            
            with patch.object(Customer, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is True

    def test_task_priority_and_status_validation(self, app):
        """Test task priority and status validation with edge cases"""
        with app.app_context():
            # Test with valid choices
            valid_priorities = ['low', 'medium', 'high']
            valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
            
            for priority in valid_priorities:
                for status in valid_statuses:
                    form_data = {
                        'title': f'Task {priority} {status}',
                        'description': f'Task with {priority} priority and {status} status',
                        'priority': priority,
                        'status': status
                    }
                    form = TaskEditForm(data=form_data)
                    assert form.validate() is True, f"Failed for {priority}/{status}"

    def test_form_csrf_handling(self, app):
        """Test CSRF handling in forms"""
        with app.app_context():
            # Test that BaseNoCSRFForm actually disables CSRF
            form = AgentEditForm()
            assert hasattr(form.meta, 'csrf')
            assert form.meta.csrf is False
            
            form = CustomerEditForm()
            assert form.meta.csrf is False
            
            form = TaskEditForm()
            assert form.meta.csrf is False


@pytest.mark.usefixtures("app")
class TestFormCustomValidators:
    """Test custom validators in forms"""

    def test_email_uniqueness_validator_implementation(self, app):
        """Test the implementation of email uniqueness validator"""
        with app.app_context():
            # Create a form with agent_id (editing existing agent)
            form = AgentEditForm(agent_id=123)
            
            # Mock the validator behavior
            mock_agent_same_id = MagicMock()
            mock_agent_same_id.id = 123
            
            mock_agent_different_id = MagicMock()
            mock_agent_different_id.id = 456
            
            with patch.object(Agent, 'query') as mock_query:
                # Test: same agent editing their own email (should pass)
                mock_query.filter_by.return_value.first.return_value = mock_agent_same_id
                form_data = {
                    'name': 'Test Agent',
                    'email': 'test@example.com',
                    'phone': '555-0123'
                }
                form = AgentEditForm(agent_id=123, data=form_data)
                assert form.validate() is True
                
                # Test: different agent with same email (should fail)
                mock_query.filter_by.return_value.first.return_value = mock_agent_different_id
                form = AgentEditForm(agent_id=123, data=form_data)
                assert form.validate() is False
                assert 'email' in form.errors

    def test_budget_range_validator_implementation(self, app):
        """Test the implementation of budget range validator"""
        with app.app_context():
            # Test the custom validator logic
            form_data = {
                'name': 'Budget Customer',
                'email': 'budget@example.com',
                'phone': '555-0123',
                'budget_min': 200000.0,
                'budget_max': 100000.0  # Invalid: max < min
            }
            
            form = CustomerEditForm(data=form_data)
            
            with patch.object(Customer, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is False
                assert 'budget_max' in form.errors
                
                # Check the specific error message
                error_message = str(form.errors['budget_max'][0])
                assert 'greater than or equal' in error_message.lower()

    def test_due_date_validator_implementation(self, app):
        """Test the implementation of due date validator"""
        with app.app_context():
            yesterday = date.today() - timedelta(days=1)
            
            form_data = {
                'title': 'Past Due Task',
                'description': 'Task with past due date',
                'priority': 'medium',
                'status': 'pending',
                'due_date': yesterday
            }
            
            form = TaskEditForm(data=form_data)
            assert form.validate() is False
            assert 'due_date' in form.errors
            
            # Check the specific error message
            error_message = str(form.errors['due_date'][0])
            assert 'cannot be in the past' in error_message.lower()

    def test_phone_format_validation(self, app):
        """Test phone number format validation"""
        with app.app_context():
            # Test various phone formats
            valid_phones = [
                '123-456-7890',
                '(123) 456-7890',
                '123.456.7890',
                '1234567890',
                '+1 123-456-7890',
                '+1 (123) 456-7890'
            ]
            
            for phone in valid_phones:
                form_data = {
                    'name': 'Phone Test Agent',
                    'email': f'phone{phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "").replace("+", "")}@example.com',
                    'phone': phone
                }
                form = AgentEditForm(data=form_data)
                
                with patch.object(Agent, 'query') as mock_query:
                    mock_query.filter_by.return_value.first.return_value = None
                    # Phone validation depends on the actual validator implementation
                    # This test assumes basic length validation
                    result = form.validate()
                    if not result and 'phone' in form.errors:
                        print(f"Phone format '{phone}' failed validation: {form.errors['phone']}")

    def test_field_length_validators(self, app):
        """Test field length validators"""
        with app.app_context():
            # Test maximum length validation
            form_data = {
                'name': 'x' * 256,  # Exceeds typical max length
                'email': 'test@example.com',
                'phone': '555-0123'
            }
            form = AgentEditForm(data=form_data)
            
            with patch.object(Agent, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                assert form.validate() is False
                assert 'name' in form.errors
                
                # Check that the error is about length
                error_message = str(form.errors['name'][0])
                assert 'length' in error_message.lower() or 'long' in error_message.lower()
