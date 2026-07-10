# schemas.py
from typing import List, Optional

from pydantic import BaseModel, field_validator


class PropertyAI(BaseModel):
    title: Optional[str] = None
    address: Optional[str] = None
    price: Optional[float] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    square_feet: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = "active"
    agent_id: Optional[int] = None
    year_built: Optional[int] = None
    parking_spaces: Optional[int] = 0
    floors: Optional[int] = 1
    units: Optional[int] = 1
    property_condition: Optional[str] = "good"
    heating_type: Optional[str] = None
    cooling_type: Optional[str] = None
    rental_price: Optional[float] = None
    property_features: Optional[List[str]] = None
    neighborhood: Optional[str] = None
    property_category: Optional[str] = "residential"
    listing_type: Optional[str] = "sale"
    rahn: Optional[float] = None  # for deposit (Iran market)
    ejare: Optional[float] = None  # for monthly rent (Iran market)

    @field_validator("property_features", mode="before")
    @classmethod
    def split_features(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v


class CustomerAI(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    preferences: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    desired_neighborhoods: Optional[List[str]] = None
    desired_property_type: Optional[str] = None
    bedrooms_min: Optional[int] = None
    bathrooms_min: Optional[int] = None

    @field_validator("desired_neighborhoods", mode="before")
    @classmethod
    def split_neighborhoods(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v
