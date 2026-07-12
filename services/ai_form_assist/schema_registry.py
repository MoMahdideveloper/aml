"""Allowlisted CRM form schemas mapped to active WTForms fields."""

from __future__ import annotations

from typing import Dict, List

from services.ai_form_assist.types import FieldDescriptor, FormSchema


class UnknownAIFormSchema(ValueError):
    def __init__(self, name: str):
        super().__init__(f"Unknown AI form schema: {name}")
        self.name = name


class UnknownAIFormField(ValueError):
    def __init__(self, name: str):
        super().__init__(f"Unknown AI form field: {name}")
        self.name = name


def _f(
    name: str,
    *,
    field_type: str = "string",
    aliases: List[str] | None = None,
    auto_fill_allowed: bool = True,
    review_only: bool = False,
    sensitive: bool = False,
    enum_values: List[str] | None = None,
    input_name: str | None = None,
) -> FieldDescriptor:
    return FieldDescriptor(
        name=name,
        input_name=input_name or name,
        field_type=field_type,
        aliases=list(aliases or []),
        auto_fill_allowed=auto_fill_allowed and not review_only,
        review_only=review_only,
        sensitive=sensitive,
        enum_values=list(enum_values or []),
    )


_REGISTRY: Dict[str, FormSchema] = {
    "property": FormSchema(
        name="property",
        fields={
            "title": _f("title", aliases=["نام", "عنوان"]),
            "address": _f("address", field_type="text", aliases=["آدرس"]),
            "property_type": _f(
                "property_type",
                aliases=["type", "نوع"],
            ),
            "bedrooms": _f("bedrooms", field_type="integer", aliases=["rooms", "خواب"]),
            "bathrooms": _f("bathrooms", field_type="integer", aliases=["حمام"]),
            "square_feet": _f(
                "square_feet", field_type="integer", aliases=["area", "متراژ", "meter"]
            ),
            "description": _f("description", field_type="text", aliases=["توضیحات"]),
            "year_built": _f("year_built", field_type="integer", aliases=["سال_ساخت"]),
            "parking_spaces": _f("parking_spaces", field_type="integer", aliases=["پارکینگ"]),
            "floors": _f("floors", field_type="integer"),
            "units": _f("units", field_type="integer"),
            "property_condition": _f("property_condition", aliases=["condition"]),
            "property_features": _f("property_features", field_type="text", aliases=["amenities"]),
            "neighborhood": _f("neighborhood", aliases=["محله"]),
            "property_category": _f("property_category"),
            "listing_type": _f(
                "listing_type",
                field_type="enum",
                enum_values=["sale", "rental"],
                aliases=["فروش", "اجاره"],
            ),
            "sale_price": _f(
                "sale_price", field_type="number", aliases=["price", "قیمت", "تومان"]
            ),
            "rahn": _f("rahn", field_type="number", aliases=["رهن", "deposit"]),
            "ejare": _f("ejare", field_type="number", aliases=["اجاره", "rent"]),
            "status": _f("status"),
            "agent_id": _f(
                "agent_id",
                field_type="id",
                review_only=True,
                auto_fill_allowed=False,
            ),
        },
    ),
    "customer": FormSchema(
        name="customer",
        fields={
            "name": _f("name", aliases=["نام"]),
            "email": _f("email", sensitive=True),
            "phone": _f("phone", field_type="string", sensitive=True, aliases=["موبایل"]),
            "budget_min": _f("budget_min", field_type="number"),
            "budget_max": _f("budget_max", field_type="number", aliases=["budget"]),
            "preferred_bedrooms": _f("preferred_bedrooms", field_type="integer"),
            "preferred_bathrooms": _f("preferred_bathrooms", field_type="integer"),
            "preferred_type": _f("preferred_type"),
            "location_preference": _f("location_preference", aliases=["location"]),
            "preferences": _f(
                "preferences", field_type="text", sensitive=True, auto_fill_allowed=False
            ),
            "customer_type": _f(
                "customer_type",
                field_type="enum",
                enum_values=["buyer", "seller", "both", "investor"],
            ),
        },
    ),
    "recommendation": FormSchema(
        name="recommendation",
        fields={
            "budget_min": _f("budget_min", field_type="number"),
            "budget_max": _f("budget_max", field_type="number"),
            "preferred_bedrooms": _f("preferred_bedrooms", field_type="integer"),
            "preferred_bathrooms": _f("preferred_bathrooms", field_type="integer"),
            "preferred_type": _f("preferred_type"),
            "location_preference": _f("location_preference"),
        },
    ),
    "deal": FormSchema(
        name="deal",
        fields={
            "property_id": _f("property_id", field_type="id", review_only=True),
            "customer_id": _f("customer_id", field_type="id", review_only=True),
            "agent_id": _f("agent_id", field_type="id", review_only=True),
            "status": _f("status"),
            "offer_amount": _f("offer_amount", field_type="number", aliases=["offer"]),
        },
    ),
    "task": FormSchema(
        name="task",
        fields={
            "title": _f("title"),
            "description": _f("description", field_type="text"),
            "agent_id": _f("agent_id", field_type="id", review_only=True),
            "priority": _f("priority", field_type="enum", enum_values=["low", "medium", "high", "urgent"]),
            "due_date": _f("due_date", field_type="date"),
        },
    ),
    "agent": FormSchema(
        name="agent",
        fields={
            "name": _f("name"),
            "email": _f("email", sensitive=True),
            "phone": _f("phone", sensitive=True),
            "specialization": _f("specialization"),
            "bio": _f("bio", field_type="text"),
        },
    ),
}


def list_form_schemas() -> List[str]:
    return sorted(_REGISTRY.keys())


def get_form_schema(name: str) -> FormSchema:
    key = (name or "").strip().lower()
    if key not in _REGISTRY:
        raise UnknownAIFormSchema(name)
    return _REGISTRY[key]
