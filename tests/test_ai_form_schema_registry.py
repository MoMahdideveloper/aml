"""AI form schema registry maps real WTForms fields."""

import pytest

from services.ai_form_assist.schema_registry import (
    UnknownAIFormField,
    UnknownAIFormSchema,
    get_form_schema,
    list_form_schemas,
)


def test_known_schemas_present():
    names = list_form_schemas()
    for required in ("property", "customer", "recommendation", "deal", "task", "agent"):
        assert required in names


def test_property_registry_maps_real_form_fields():
    schema = get_form_schema("property")
    assert schema.fields["sale_price"].input_name == "sale_price"
    assert schema.fields["rahn"].input_name == "rahn"
    assert schema.fields["ejare"].input_name == "ejare"
    assert schema.fields["title"].input_name == "title"
    assert schema.fields["agent_id"].review_only is True
    assert schema.fields["agent_id"].auto_fill_allowed is False


def test_customer_sensitive_fields():
    schema = get_form_schema("customer")
    assert schema.fields["email"].sensitive is True
    assert schema.fields["phone"].sensitive is True


def test_unknown_schema_raises():
    with pytest.raises(UnknownAIFormSchema):
        get_form_schema("not_a_form")


def test_unknown_model_field_is_rejected():
    with pytest.raises(UnknownAIFormField):
        get_form_schema("property").require_field("database_admin")
