from datetime import datetime
from typing import Dict, List, Optional


class Property:
    def __init__(
        self,
        id: int,
        title: str,
        address: str,
        price: float,
        property_type: str,
        bedrooms: int,
        bathrooms: int,
        square_feet: int,
        description: str,
        status: str = "active",
        agent_id: Optional[int] = None,
        year_built: Optional[int] = None,
        parking_spaces: int = 0,
        floors: int = 1,
        units: int = 1,
        property_condition: str = "good",
        heating_type: str = "",
        cooling_type: str = "",
        rental_price: Optional[float] = None,
        property_features: str = "",
        neighborhood: str = "",
        property_category: str = "residential",
        listing_type: str = "sale",
        rahn: Optional[float] = None,
        ejare: Optional[float] = None,
    ):
        self.id = id
        self.title = title
        self.address = address
        self.price = price
        self.property_type = property_type
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.square_feet = square_feet
        self.description = description
        self.status = status
        self.agent_id = agent_id

        # Enhanced fields inspired by the images
        self.year_built = year_built
        self.parking_spaces = parking_spaces
        self.floors = floors
        self.units = units
        self.property_condition = property_condition  # excellent, good, fair, needs_renovation
        self.heating_type = heating_type
        self.cooling_type = cooling_type
        self.rental_price = rental_price
        self.property_features = property_features  # comma-separated features
        self.neighborhood = neighborhood
        self.property_category = property_category  # residential, commercial, industrial

        # Iranian real estate pricing system
        self.listing_type = listing_type  # "sale" or "rental"
        self.rahn = rahn  # Deposit amount for rentals in Iranian system
        self.ejare = ejare  # Monthly rent amount for rentals in Iranian system

        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "address": self.address,
            "price": self.price,
            "property_type": self.property_type,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "square_feet": self.square_feet,
            "description": self.description,
            "status": self.status,
            "agent_id": self.agent_id,
            "year_built": self.year_built,
            "parking_spaces": self.parking_spaces,
            "floors": self.floors,
            "units": self.units,
            "property_condition": self.property_condition,
            "heating_type": self.heating_type,
            "cooling_type": self.cooling_type,
            "rental_price": self.rental_price,
            "property_features": self.property_features,
            "neighborhood": self.neighborhood,
            "property_category": self.property_category,
            "listing_type": self.listing_type,
            "rahn": self.rahn,
            "ejare": self.ejare,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @property
    def age(self) -> Optional[int]:
        """Calculate property age"""
        if self.year_built:
            return datetime.now().year - self.year_built
        return None

    @property
    def features_list(self) -> List[str]:
        """Get property features as a list"""
        if self.property_features:
            return [feature.strip() for feature in self.property_features.split(",")]
        return []

    @property
    def price_per_sqft(self) -> float:
        """Calculate price per square foot"""
        if self.square_feet > 0:
            return self.price / self.square_feet
        return 0

    @property
    def rahn_per_meter(self) -> float:
        """Calculate rahn (deposit) per square meter for rentals"""
        if self.listing_type == "rental" and self.rahn and self.square_feet > 0:
            return self.rahn / self.square_feet
        return 0

    @property
    def ejare_per_meter(self) -> float:
        """Calculate ejare (monthly rent) per square meter for rentals"""
        if self.listing_type == "rental" and self.ejare and self.square_feet > 0:
            return self.ejare / self.square_feet
        return 0

    @property
    def sale_price_per_meter(self) -> float:
        """Calculate sale price per square meter for sales"""
        if self.listing_type == "sale" and self.price and self.square_feet > 0:
            return self.price / self.square_feet
        return 0


class Agent:
    def __init__(
        self, id: int, name: str, email: str, phone: str, specialization: str = "", bio: str = ""
    ):
        self.id = id
        self.name = name
        self.email = email
        self.phone = phone
        self.specialization = specialization
        self.bio = bio
        self.created_at = datetime.now()
        self.total_sales = 0
        self.active_listings = 0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "specialization": self.specialization,
            "bio": self.bio,
            "created_at": self.created_at.isoformat(),
            "total_sales": self.total_sales,
            "active_listings": self.active_listings,
        }


class Customer:
    def __init__(
        self,
        id: int,
        name: str,
        email: str,
        phone: str,
        budget_min: float = 0,
        budget_max: float = 0,
        preferred_bedrooms: int = 0,
        preferred_bathrooms: int = 0,
        preferred_type: str = "",
        location_preference: str = "",
    ):
        self.id = id
        self.name = name
        self.email = email
        self.phone = phone
        self.budget_min = budget_min
        self.budget_max = budget_max
        self.preferred_bedrooms = preferred_bedrooms
        self.preferred_bathrooms = preferred_bathrooms
        self.preferred_type = preferred_type
        self.location_preference = location_preference
        self.created_at = datetime.now()
        self.status = "active"

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "preferred_bedrooms": self.preferred_bedrooms,
            "preferred_bathrooms": self.preferred_bathrooms,
            "preferred_type": self.preferred_type,
            "location_preference": self.location_preference,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
        }


class Deal:
    def __init__(
        self,
        id: int,
        property_id: int,
        customer_id: int,
        agent_id: int,
        status: str = "prospecting",
        offer_amount: float = 0,
    ):
        self.id = id
        self.property_id = property_id
        self.customer_id = customer_id
        self.agent_id = agent_id
        self.status = (
            status  # prospecting, qualified, proposal, negotiation, closed_won, closed_lost
        )
        self.offer_amount = offer_amount
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.notes = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "property_id": self.property_id,
            "customer_id": self.customer_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "offer_amount": self.offer_amount,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "notes": self.notes,
        }


class Task:
    def __init__(
        self,
        id: int,
        title: str,
        description: str,
        agent_id: int,
        priority: str = "medium",
        status: str = "pending",
        due_date: Optional[datetime] = None,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.agent_id = agent_id
        self.priority = priority  # low, medium, high
        self.status = status  # pending, completed, overdue
        self.due_date = due_date
        self.created_at = datetime.now()
        self.completed_at = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "agent_id": self.agent_id,
            "priority": self.priority,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
