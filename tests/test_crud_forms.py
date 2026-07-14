"""
Unit tests for CRUD form validation logic.

Tests are written against the actual form classes in forms.py:
AgentForm, CustomerForm, TaskForm (all extend BaseNoCSRFForm).
"""

import pytest
from werkzeug.datastructures import ImmutableMultiDict

from forms import AgentForm, CustomerForm, TaskForm


# ---------------------------------------------------------------------------
# AgentForm
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("app")
class TestAgentForm:
    """Validates AgentForm field requirements and constraints."""

    def test_valid_minimal(self, app):
        with app.app_context():
            form = AgentForm(data={
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "555-0123",
            })
            assert form.validate() is True

    def test_valid_with_optional_fields(self, app):
        with app.app_context():
            form = AgentForm(data={
                "name": "Jane Smith",
                "email": "jane@example.com",
                "phone": "555-0456",
                "specialization": "Residential Sales",
                "bio": "Experienced agent",
            })
            assert form.validate() is True

    def test_required_fields_missing(self, app):
        with app.app_context():
            form = AgentForm(data={})
            assert form.validate() is False
            assert "name" in form.errors
            assert "email" in form.errors
            assert "phone" in form.errors

    def test_invalid_email_format(self, app):
        with app.app_context():
            form = AgentForm(data={
                "name": "John Doe",
                "email": "not-an-email",
                "phone": "555-0123",
            })
            assert form.validate() is False
            assert "email" in form.errors

    def test_name_exceeds_max_length(self, app):
        with app.app_context():
            form = AgentForm(data={
                "name": "x" * 256,
                "email": "test@example.com",
                "phone": "555-0123",
            })
            assert form.validate() is False
            assert "name" in form.errors

    def test_phone_exceeds_max_length(self, app):
        with app.app_context():
            form = AgentForm(data={
                "name": "John Doe",
                "email": "test@example.com",
                "phone": "5" * 51,
            })
            assert form.validate() is False
            assert "phone" in form.errors

    def test_optional_fields_absent_does_not_error(self, app):
        with app.app_context():
            form = AgentForm(data={
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "555-0123",
            })
            assert form.validate() is True
            assert "specialization" not in form.errors
            assert "bio" not in form.errors

    def test_empty_optional_fields_do_not_error(self, app):
        with app.app_context():
            form = AgentForm(data={
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "555-0123",
                "specialization": "",
                "bio": "",
            })
            assert form.validate() is True

    def test_csrf_disabled(self, app):
        with app.app_context():
            assert AgentForm().meta.csrf is False

    def test_unicode_name(self, app):
        with app.app_context():
            form = AgentForm(data={
                "name": "José María González",
                "email": "jose@example.com",
                "phone": "+1 555-0123",
            })
            assert form.validate() is True

    def test_special_chars_in_name(self, app):
        with app.app_context():
            form = AgentForm(data={
                "name": "Agent with 'quotes' & symbols",
                "email": "special+test@example-domain.com",
                "phone": "(555) 123-4567",
            })
            assert form.validate() is True

    def test_empty_required_strings_fail(self, app):
        with app.app_context():
            form = AgentForm(data={
                "name": "",
                "email": "",
                "phone": "",
            })
            assert form.validate() is False
            assert "name" in form.errors
            assert "email" in form.errors
            assert "phone" in form.errors


# ---------------------------------------------------------------------------
# CustomerForm
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("app")
class TestCustomerForm:
    """Validates CustomerForm field requirements and constraints."""

    def test_valid_minimal(self, app):
        with app.app_context():
            form = CustomerForm(data={
                "name": "Jane Smith",
                "email": "jane.smith@example.com",
                "phone": "555-0456",
            })
            assert form.validate() is True

    def test_valid_with_budget(self, app):
        with app.app_context():
            form = CustomerForm(data={
                "name": "Jane Smith",
                "email": "jane@example.com",
                "phone": "555-0456",
                "budget_min": 100000.0,
                "budget_max": 200000.0,
            })
            assert form.validate() is True

    def test_required_fields_missing(self, app):
        with app.app_context():
            form = CustomerForm(data={})
            assert form.validate() is False
            assert "name" in form.errors
            assert "email" in form.errors
            assert "phone" in form.errors

    def test_invalid_email_format(self, app):
        with app.app_context():
            form = CustomerForm(data={
                "name": "Jane Smith",
                "email": "bad-email",
                "phone": "555-0456",
            })
            assert form.validate() is False
            assert "email" in form.errors

    def test_negative_budget_min_rejected(self, app):
        # Optional() skips NumberRange when raw_data is absent; use formdata
        # so raw_data is populated and the full validator chain runs.
        with app.app_context():
            form = CustomerForm(formdata=ImmutableMultiDict([
                ("name", "Jane Smith"),
                ("email", "jane@example.com"),
                ("phone", "555-0456"),
                ("budget_min", "-1000.0"),
            ]))
            assert form.validate() is False
            assert "budget_min" in form.errors

    def test_negative_budget_max_rejected(self, app):
        with app.app_context():
            form = CustomerForm(formdata=ImmutableMultiDict([
                ("name", "Jane Smith"),
                ("email", "jane@example.com"),
                ("phone", "555-0456"),
                ("budget_max", "-500.0"),
            ]))
            assert form.validate() is False
            assert "budget_max" in form.errors

    def test_zero_budget_min_valid(self, app):
        with app.app_context():
            form = CustomerForm(data={
                "name": "Jane Smith",
                "email": "jane@example.com",
                "phone": "555-0456",
                "budget_min": 0.0,
            })
            assert form.validate() is True

    def test_optional_preferences_absent(self, app):
        with app.app_context():
            form = CustomerForm(data={
                "name": "Jane Smith",
                "email": "jane@example.com",
                "phone": "555-0456",
            })
            assert form.validate() is True
            assert "preferred_bedrooms" not in form.errors
            assert "preferred_bathrooms" not in form.errors
            assert "preferred_type" not in form.errors
            assert "location_preference" not in form.errors

    def test_valid_customer_type_choices(self, app):
        # Use formdata= so SelectField.pre_validate runs against raw_data, not
        # the Python object path which bypasses the choices check.
        with app.app_context():
            for customer_type in ("buyer", "seller", "both", "investor"):
                form = CustomerForm(formdata=ImmutableMultiDict([
                    ("name", "Jane Smith"),
                    ("email", "jane@example.com"),
                    ("phone", "555-0456"),
                    ("customer_type", customer_type),
                ]))
                assert form.validate() is True, f"customer_type={customer_type} should be valid"

    def test_invalid_customer_type_rejected(self, app):
        # SelectField.pre_validate must reject values not in choices.
        with app.app_context():
            form = CustomerForm(formdata=ImmutableMultiDict([
                ("name", "Jane Smith"),
                ("email", "jane@example.com"),
                ("phone", "555-0456"),
                ("customer_type", "invalid_choice"),
            ]))
            assert form.validate() is False
            assert "customer_type" in form.errors

    def test_csrf_disabled(self, app):
        with app.app_context():
            assert CustomerForm().meta.csrf is False

    def test_extreme_budget_values_valid(self, app):
        with app.app_context():
            form = CustomerForm(data={
                "name": "Rich Client",
                "email": "rich@example.com",
                "phone": "555-0123",
                "budget_min": 0.01,
                "budget_max": 999999999.99,
            })
            assert form.validate() is True

    def test_preferences_text_within_limit(self, app):
        with app.app_context():
            form = CustomerForm(data={
                "name": "Jane Smith",
                "email": "jane@example.com",
                "phone": "555-0456",
                "preferences": "x" * 4000,
            })
            assert form.validate() is True

    def test_preferences_text_exceeds_limit(self, app):
        with app.app_context():
            form = CustomerForm(formdata=ImmutableMultiDict([
                ("name", "Jane Smith"),
                ("email", "jane@example.com"),
                ("phone", "555-0456"),
                ("preferences", "x" * 4001),
            ]))
            assert form.validate() is False
            assert "preferences" in form.errors


# ---------------------------------------------------------------------------
# TaskForm
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("app")
class TestTaskForm:
    """Validates TaskForm field requirements and constraints."""

    def test_valid_minimal(self, app):
        with app.app_context():
            form = TaskForm(data={
                "title": "Follow up with client",
                "agent_id": 1,
            })
            assert form.validate() is True

    def test_valid_full(self, app):
        with app.app_context():
            form = TaskForm(data={
                "title": "Follow up with client",
                "description": "Call client to discuss property options",
                "agent_id": 1,
                "priority": "medium",
                "due_date": "2099-12-31",
            })
            assert form.validate() is True

    def test_title_required(self, app):
        with app.app_context():
            form = TaskForm(data={"agent_id": 1})
            assert form.validate() is False
            assert "title" in form.errors

    def test_agent_id_required(self, app):
        with app.app_context():
            form = TaskForm(data={"title": "My Task"})
            assert form.validate() is False
            assert "agent_id" in form.errors

    def test_agent_id_must_be_positive(self, app):
        with app.app_context():
            form = TaskForm(data={"title": "My Task", "agent_id": 0})
            assert form.validate() is False
            assert "agent_id" in form.errors

    def test_title_exceeds_max_length(self, app):
        with app.app_context():
            form = TaskForm(data={
                "title": "x" * 256,
                "agent_id": 1,
            })
            assert form.validate() is False
            assert "title" in form.errors

    def test_priority_within_max_length(self, app):
        with app.app_context():
            form = TaskForm(data={
                "title": "Task",
                "agent_id": 1,
                "priority": "x" * 20,
            })
            assert form.validate() is True

    def test_priority_exceeds_max_length(self, app):
        with app.app_context():
            form = TaskForm(formdata=ImmutableMultiDict([
                ("title", "Task"),
                ("agent_id", "1"),
                ("priority", "x" * 21),
            ]))
            assert form.validate() is False
            assert "priority" in form.errors

    def test_description_optional(self, app):
        with app.app_context():
            form = TaskForm(data={"title": "Task", "agent_id": 1})
            assert form.validate() is True
            assert "description" not in form.errors

    def test_due_date_optional(self, app):
        with app.app_context():
            form = TaskForm(data={"title": "Task", "agent_id": 1})
            assert form.validate() is True
            assert "due_date" not in form.errors

    def test_csrf_disabled(self, app):
        with app.app_context():
            assert TaskForm().meta.csrf is False

    def test_long_description_valid(self, app):
        with app.app_context():
            form = TaskForm(data={
                "title": "Task with long description",
                "description": "x" * 5000,
                "agent_id": 1,
            })
            assert form.validate() is True


# ---------------------------------------------------------------------------
# BaseNoCSRFForm inheritance
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("app")
class TestBaseNoCSRFFormInheritance:
    """Confirms all edit forms inherit CSRF-disabled meta from BaseNoCSRFForm."""

    def test_all_forms_have_csrf_disabled(self, app):
        with app.app_context():
            for form_cls in (AgentForm, CustomerForm, TaskForm):
                assert form_cls().meta.csrf is False, (
                    f"{form_cls.__name__} should have csrf=False"
                )
