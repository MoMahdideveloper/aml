import random
import string
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import db


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SuggestionItem(db.Model):
    __tablename__ = "suggestion_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Add other fields as needed by the test
    # For now, we'll add a placeholder to satisfy the import
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class AnalysisTemplate(db.Model):
    __tablename__ = "analysis_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)
    configuration: Mapped[Optional[str]] = mapped_column(Text)  # JSON string
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive)

    # Relationship
    reports = relationship("AnalysisReport", back_populates="template", cascade="all, delete-orphan")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "analysis_type": self.analysis_type,
            "configuration": self.configuration,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AnalysisReport(db.Model):
    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("analysis_templates.id"), nullable=False)
    # Add other fields as needed by the test
    # For now, we'll keep it simple to satisfy the import
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    # Relationship
    template = relationship("AnalysisTemplate", back_populates="reports")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Property(db.Model):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[int] = mapped_column(BigInteger, default=0)
    property_type: Mapped[str] = mapped_column(String(50), nullable=False)
    bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    bathrooms: Mapped[int] = mapped_column(Integer, default=0)
    square_feet: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    is_ai_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual, maskan, autofill

    # Enhanced fields
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parking_spaces: Mapped[int] = mapped_column(Integer, default=0)
    floors: Mapped[int] = mapped_column(Integer, default=1)
    units: Mapped[int] = mapped_column(Integer, default=1)
    property_condition: Mapped[str] = mapped_column(String(50), default="good")
    heating_type: Mapped[str] = mapped_column(String(50), default="")
    cooling_type: Mapped[str] = mapped_column(String(50), default="")
    rental_price: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    property_features: Mapped[str] = mapped_column(Text, default="")
    neighborhood: Mapped[str] = mapped_column(String(100), default="")
    property_category: Mapped[str] = mapped_column(String(50), default="residential")

    # Iranian real estate pricing system
    listing_type: Mapped[str] = mapped_column(String(20), default="sale")
    rahn: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # Deposit for rentals
    ejare: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # Monthly rent

    # Gap-fill fields (maskan-file.ir parity)
    file_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)  # Unique listing code
    floor_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Unit's floor in building
    has_storage: Mapped[bool] = mapped_column(Boolean, default=False)
    has_elevator: Mapped[bool] = mapped_column(Boolean, default=False)
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. 'sandi', 'manghuleh', etc.
    built_area: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Built area (bana) in sqm
    land_area: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Lot/land area in sqm
    floor_covering: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. ceramic, parquet
    facade_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. stone, brick
    wall_covering: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. paint, wallpaper
    cabinet_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. mdf, metal
    property_direction: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # e.g. north, south
    is_exchangeable: Mapped[bool] = mapped_column(Boolean, default=False)  # "ghabeliat moavaze"
    boundary_width: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Hashiye-ye melk
    density: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Tarakom
    commercial_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Tejari status
    usage_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Karbari
    ceiling_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    permit_ceiling: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Saghf parvane
    property_length: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    property_height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_per_meter: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    custom_fields: Mapped[str] = mapped_column(Text, default="")  # Raw/custom Maskan fields (JSON/text)

    # Media and Location
    image_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Foreign Keys
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agents.id"), nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="properties")
    deals = relationship("Deal", back_populates="property")

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
            "file_code": self.file_code,
            "floor_number": self.floor_number,
            "has_storage": self.has_storage,
            "has_elevator": self.has_elevator,
            "document_type": self.document_type,
            "built_area": self.built_area,
            "land_area": self.land_area,
            "floor_covering": self.floor_covering,
            "facade_type": self.facade_type,
            "wall_covering": self.wall_covering,
            "cabinet_type": self.cabinet_type,
            "property_direction": self.property_direction,
            "is_exchangeable": self.is_exchangeable,
            "boundary_width": self.boundary_width,
            "density": self.density,
            "commercial_status": self.commercial_status,
            "usage_type": self.usage_type,
            "ceiling_count": self.ceiling_count,
            "permit_ceiling": self.permit_ceiling,
            "property_length": self.property_length,
            "property_height": self.property_height,
            "price_per_meter": self.price_per_meter,
            "custom_fields": self.custom_fields,
            "image_filename": self.image_filename,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
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

    @property
    def favorites_count(self) -> int:
        """Get the total number of times this property has been favorited"""
        return len(self.favorites) if hasattr(self, 'favorites') else 0

    def is_favorited_by_user(self, user_id: Optional[int] = None) -> bool:
        """Check if this property is favorited by a specific user"""
        if not hasattr(self, 'favorites'):
            return False
        
        if user_id is None:
            # For now, check if any favorites exist (future user system integration)
            return len(self.favorites) > 0
        
        return any(fav.user_id == user_id for fav in self.favorites)


def _generate_file_code():
    """Generate a unique 6-digit file code like maskan-file.ir"""
    return ''.join(random.choices(string.digits, k=6))


@event.listens_for(Property, 'before_insert')
def _set_file_code(mapper, connection, target):
    """Auto-generate file_code for new properties if not set"""
    if not target.file_code:
        target.file_code = _generate_file_code()


class PropertyImage(db.Model):
    """Stores multiple images per property for gallery support"""
    __tablename__ = "property_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    caption: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    property = relationship("Property", backref="images")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "property_id": self.property_id,
            "filename": self.filename,
            "caption": self.caption,
            "display_order": self.display_order,
            "is_primary": self.is_primary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PropertyActivityLog(db.Model):
    """Tracks property lifecycle events (created, edited, price changed, etc.)"""
    __tablename__ = "property_activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # created, updated, price_changed, status_changed
    description: Mapped[str] = mapped_column(Text, default="")
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_source: Mapped[str] = mapped_column(String(20), default="manual")  # 'sync', 'manual', 'rollback'
    changed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # user email or 'system'
    sync_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # links to SyncState.id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    property = relationship("Property", backref="activity_logs")

    __table_args__ = (
        db.Index('idx_activity_log_property_id', 'property_id'),
        db.Index('idx_activity_log_change_source', 'change_source'),
    )

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "property_id": self.property_id,
            "action": self.action,
            "description": self.description,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "change_source": self.change_source,
            "changed_by": self.changed_by,
            "sync_version": self.sync_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ContactReveal(db.Model):
    """Tracks when users reveal owner/agent contact info on a listing"""
    __tablename__ = "contact_reveals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id"), nullable=False)
    viewer_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    viewer_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    property = relationship("Property", backref="contact_reveals")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "property_id": self.property_id,
            "viewer_user_id": self.viewer_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CustomerGroup(db.Model):
    """Groups/segments for organizing customers (e.g. VIP, Investor, First-time buyer)"""
    __tablename__ = "customer_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")  # hex color for badge
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    customers = relationship("Customer", back_populates="group")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "description": self.description,
            "customer_count": len(self.customers) if self.customers else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Builder(db.Model):
    """Construction company / builder database for new developments"""
    __tablename__ = "builders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    speciality: Mapped[str] = mapped_column(String(100), default="residential")  # residential, commercial, mixed
    active_projects: Mapped[int] = mapped_column(Integer, default=0)
    completed_projects: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 1-5 stars
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "company_name": self.company_name,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "speciality": self.speciality,
            "active_projects": self.active_projects,
            "completed_projects": self.completed_projects,
            "rating": self.rating,
            "notes": self.notes,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Agent(db.Model):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    specialization: Mapped[str] = mapped_column(String(255), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    total_sales: Mapped[int] = mapped_column(Integer, default=0)
    active_listings: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    properties = relationship("Property", back_populates="agent")
    deals = relationship("Deal", back_populates="agent")
    tasks = relationship("Task", back_populates="agent")

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
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class Customer(db.Model):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    budget_min: Mapped[int] = mapped_column(BigInteger, default=0)
    budget_max: Mapped[int] = mapped_column(BigInteger, default=0)
    preferred_bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    preferred_bathrooms: Mapped[int] = mapped_column(Integer, default=0)
    preferred_type: Mapped[str] = mapped_column(String(50), default="")
    location_preference: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    # buyer = looking to purchase/rent; seller = listing/selling; both = investor or dual-sided
    customer_type: Mapped[str] = mapped_column(String(20), default="buyer")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Customer segmentation
    customer_group_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("customer_groups.id"), nullable=True)
    preferences: Mapped[str] = mapped_column(Text, default="")  # free-text preferences / notes

    # Relationships
    deals = relationship("Deal", back_populates="customer")
    group = relationship("CustomerGroup", back_populates="customers")

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
            "customer_type": getattr(self, "customer_type", None) or "buyer",
            "customer_group_id": self.customer_group_id,
            "group_name": self.group.name if self.group else None,
            "preferences": self.preferences,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class Deal(db.Model):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(50), default="prospecting")
    offer_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Foreign Keys
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agents.id"), nullable=True)

    # Relationships
    property = relationship("Property", back_populates="deals")
    customer = relationship("Customer", back_populates="deals")
    agent = relationship("Agent", back_populates="deals")

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
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class Task(db.Model):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Foreign Keys
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    # Automation provenance (nullable — manual tasks leave blank)
    automation_run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    automation_rule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    automation_title_key: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    source_entity_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="tasks")

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
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "automation_run_id": self.automation_run_id,
            "automation_rule_id": self.automation_rule_id,
        }


class EnvironmentVariable(db.Model):
    __tablename__ = "environment_variables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    change_logs = relationship("EnvironmentChangeLog", back_populates="environment_variable")

    def to_dict(self, mask_sensitive: bool = True) -> Dict:
        """Convert to dictionary with optional sensitive value masking"""
        value = self.value
        if mask_sensitive and self.is_sensitive:
            value = "*" * min(len(self.value), 8) if self.value else ""
        
        return {
            "id": self.id,
            "key": self.key,
            "value": value,
            "description": self.description,
            "is_sensitive": self.is_sensitive,
            "is_required": self.is_required,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }


class EnvironmentChangeLog(db.Model):
    __tablename__ = "environment_change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variable_key: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # 'CREATE', 'UPDATE', 'DELETE'
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    # Foreign Keys
    environment_variable_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("environment_variables.id"), nullable=True
    )

    # Relationships
    environment_variable = relationship("EnvironmentVariable", back_populates="change_logs")

    def to_dict(self, mask_sensitive: bool = True) -> Dict:
        """Convert to dictionary with optional sensitive value masking"""
        old_value = self.old_value
        new_value = self.new_value
        
        # Mask sensitive values in change log if needed
        if mask_sensitive and self.environment_variable and self.environment_variable.is_sensitive:
            old_value = "*" * min(len(self.old_value), 8) if self.old_value else None
            new_value = "*" * min(len(self.new_value), 8) if self.new_value else None
        
        return {
            "id": self.id,
            "variable_key": self.variable_key,
            "action": self.action,
            "old_value": old_value,
            "new_value": new_value,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "environment_variable_id": self.environment_variable_id,
        }


class CustomerOpportunityBrief(db.Model):
    """
    One client's need / goal. A person can have many:
    e.g. buy apartment, sell current villa, exchange home, invest cash.
    Each brief drives its own opportunity list (client-side, not agent KPIs).
    """

    __tablename__ = "customer_opportunity_briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False, index=True)

    # Short label shown in list: "Buy 3bd Jordan", "Sell family villa", "Exchange for larger"
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="Opportunity")
    # buyer | seller | exchange | investor
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="buyer")

    budget_min: Mapped[int] = mapped_column(BigInteger, default=0)
    budget_max: Mapped[int] = mapped_column(BigInteger, default=0)
    preferred_bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    preferred_bathrooms: Mapped[int] = mapped_column(Integer, default=0)
    preferred_type: Mapped[str] = mapped_column(String(50), default="")
    location_preference: Mapped[str] = mapped_column(String(255), default="")
    preferences: Mapped[str] = mapped_column(Text, default="")  # free text / must-haves

    # Optional: client's current home (sell / exchange)
    related_property_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("properties.id"), nullable=True
    )
    # For exchange: what they want in return
    exchange_notes: Mapped[str] = mapped_column(Text, default="")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )

    customer = relationship("Customer", backref="opportunity_briefs")
    related_property = relationship("Property", foreign_keys=[related_property_id])

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "title": self.title,
            "role": self.role,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "preferred_bedrooms": self.preferred_bedrooms,
            "preferred_bathrooms": self.preferred_bathrooms,
            "preferred_type": self.preferred_type,
            "location_preference": self.location_preference,
            "preferences": self.preferences,
            "related_property_id": self.related_property_id,
            "exchange_notes": self.exchange_notes,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
        }


class PropertyMatch(db.Model):
    """Stores property-customer matches generated by the background matching system"""
    __tablename__ = "property_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    # Optional link to a specific need/brief for this customer
    brief_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("customer_opportunity_briefs.id"), nullable=True, index=True
    )
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agents.id"), nullable=True)
    
    # Match scoring and analysis
    match_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 to 1.0
    confidence_level: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high
    match_reasons: Mapped[str] = mapped_column(Text, default="")  # JSON array of reasons
    
    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, reviewed, dismissed
    priority: Mapped[str] = mapped_column(String(20), default="normal")  # low, normal, high, urgent
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    property = relationship("Property", backref="matches")
    customer = relationship("Customer", backref="property_matches")
    agent = relationship("Agent", backref="property_matches")
    notifications = relationship("AgentNotification", back_populates="property_match", cascade="all, delete-orphan")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "property_id": self.property_id,
            "customer_id": self.customer_id,
            "agent_id": self.agent_id,
            "match_score": self.match_score,
            "confidence_level": self.confidence_level,
            "match_reasons": self.match_reasons,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


class PropertyFavorite(db.Model):
    """Stores user favorites for properties"""
    __tablename__ = "property_favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id"), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Future user system integration
    
    # Optional categorization and notes
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )
    
    # Relationships
    property = relationship("Property", backref="favorites")
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_property_favorites_property_id', 'property_id'),
        db.Index('idx_property_favorites_user_id', 'user_id'),
        db.Index('idx_property_favorites_property_user', 'property_id', 'user_id'),
    )

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "property_id": self.property_id,
            "user_id": self.user_id,
            "category": self.category,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentNotification(db.Model):
    """Stores notifications for agents about property matches and other events"""
    __tablename__ = "agent_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    property_match_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("property_matches.id"), nullable=True)
    
    # Notification content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), default="property_match")  # property_match, system, reminder
    
    # Status and priority
    status: Mapped[str] = mapped_column(String(20), default="unread")  # unread, read, dismissed
    priority: Mapped[str] = mapped_column(String(20), default="normal")  # low, normal, high, urgent
    
    # Delivery tracking
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    email_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship("Agent", backref="notifications")
    property_match = relationship("PropertyMatch", back_populates="notifications")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "property_match_id": self.property_match_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "status": self.status,
            "priority": self.priority,
            "email_sent": self.email_sent,
            "email_sent_at": self.email_sent_at.isoformat() if self.email_sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }

    def mark_as_read(self):
        """Mark notification as read with timestamp"""
        self.status = "read"
        self.read_at = _utcnow_naive()
        
    def dismiss(self):
        """Dismiss notification"""
        self.status = "dismissed"


class PropertyEmbedding(db.Model):
    """Stores property embeddings for vector search (pgvector-ready, JSON-compatible)."""
    __tablename__ = "property_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id"), unique=True, nullable=False)
    # JSON list of floats for cross-db compatibility; migration adds pgvector column for Postgres.
    embedding_data: Mapped[str] = mapped_column(Text, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="gemini")
    dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=768)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )

    property = relationship("Property", backref="embedding")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "property_id": self.property_id,
            "source_hash": self.source_hash,
            "provider": self.provider,
            "dimension": self.dimension,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MatchingJobRun(db.Model):
    """Tracks matching cycles for idempotency and observability."""
    __tablename__ = "matching_job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running, completed, failed, skipped
    trigger_source: Mapped[str] = mapped_column(String(30), default="scheduled")
    property_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "idempotency_key": self.idempotency_key,
            "status": self.status,
            "trigger_source": self.trigger_source,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


class RematchQueue(db.Model):
    """Queue of rematch requests produced by model change events."""
    __tablename__ = "rematch_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # property|customer
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(120), default="model_change")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|processing|done|failed
    retries: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "reason": self.reason,
            "status": self.status,
            "retries": self.retries,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AutomationRule(db.Model):
    """Rule definition for workflow automations."""
    __tablename__ = "automation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # JSON payloads stored as text for cross-db compatibility.
    conditions: Mapped[str] = mapped_column(Text, default="{}")
    actions: Mapped[str] = mapped_column(Text, default="[]")
    created_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )
    # Follow-up automation extensions
    rule_key: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, unique=True)
    cooldown_hours: Mapped[int] = mapped_column(Integer, default=24)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_type": self.trigger_type,
            "enabled": self.enabled,
            "conditions": self.conditions,
            "actions": self.actions,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "rule_key": self.rule_key,
            "cooldown_hours": self.cooldown_hours,
            "priority": self.priority,
            "version": self.version,
            "is_template": self.is_template,
        }


class AutomationAuditLog(db.Model):
    """Audit records for automation executions."""
    __tablename__ = "automation_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("automation_rules.id"), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="success")  # success|failed|skipped
    details: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    rule = relationship("AutomationRule", backref="audit_logs")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "trigger_type": self.trigger_type,
            "trigger_ref": self.trigger_ref,
            "status": self.status,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(db.Model):
    """User authentication and profile management"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="agent")  # admin, agent, viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)



    def set_password(self, password: str):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role,
            "is_active": self.is_active,

            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }





class PublicPropertySubmission(db.Model):
    """Public property submission form entries (no login required)"""
    __tablename__ = "public_property_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submitter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    submitter_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    submitter_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    property_title: Mapped[str] = mapped_column(String(255), nullable=False)
    property_type: Mapped[str] = mapped_column(String(50), default="apartment")
    listing_type: Mapped[str] = mapped_column(String(20), default="sale")
    address: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    rahn: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ejare: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    square_feet: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    admin_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "submitter_name": self.submitter_name,
            "submitter_phone": self.submitter_phone,
            "submitter_email": self.submitter_email,
            "property_title": self.property_title,
            "property_type": self.property_type,
            "listing_type": self.listing_type,
            "address": self.address,
            "price": self.price,
            "rahn": self.rahn,
            "ejare": self.ejare,
            "bedrooms": self.bedrooms,
            "square_feet": self.square_feet,
            "description": self.description,
            "status": self.status,
            "admin_notes": self.admin_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OpenHouseCheckin(db.Model):
    """Guest registration captured at open-house kiosk mode."""
    __tablename__ = "open_house_checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    status_tags: Mapped[str] = mapped_column(String(255), default="")  # pipe-separated preferences
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("customers.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, index=True)

    property = relationship("Property", backref="open_house_checkins")
    customer = relationship("Customer", backref="open_house_checkins")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "property_id": self.property_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "status_tags": self.status_tags,
            "customer_id": self.customer_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ClientMessage(db.Model):
    """In-app CRM messages between agents and clients (messaging portal)."""
    __tablename__ = "client_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agents.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # outbound = agent → client, inbound = client → agent (logged notes / replies)
    direction: Mapped[str] = mapped_column(String(20), default="outbound")
    channel: Mapped[str] = mapped_column(String(20), default="app")  # app, sms, email
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, index=True)

    customer = relationship("Customer", backref="messages")
    agent = relationship("Agent", backref="client_messages")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "agent_id": self.agent_id,
            "body": self.body,
            "direction": self.direction,
            "channel": self.channel,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SmsOutboundMessage(db.Model):
    """Queued outbound SMS message for asynchronous provider delivery."""
    __tablename__ = "sms_outbound_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="melipayamak")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, sent, failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )

    created_by_user = relationship("User", backref="sms_outbound_messages")

    __table_args__ = (
        db.Index("ix_sms_outbound_messages_status_created", "status", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "recipient": self.recipient,
            "message": self.message,
            "provider": self.provider,
            "status": self.status,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "error_message": self.error_message,
            "provider_message_id": self.provider_message_id,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class PropertyAIHistory(db.Model):
    __tablename__ = 'property_ai_history'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey('properties.id'), nullable=False)
    raw_data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    user_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    property = relationship('Property', backref='ai_history')

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'property_id': self.property_id,
            'raw_data': self.raw_data,
            'created_at': self.created_at.isoformat(),
            'user_note': self.user_note,
        }


class ModelPerformanceMetric(db.Model):
    """Tracks AI model performance metrics for monitoring and optimization."""
    __tablename__ = "model_performance_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g., 'gemini-pro', 'gemini-ultra'
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # latency, token_usage, success_rate, etc.
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, index=True)
    # Optional metadata for context (operation type, request ID, etc.)
    metadata_: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            "id": self.id,
            "model_name": self.model_name,
            "metric_type": self.metric_type,
            "metric_value": self.metric_value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": json.loads(self.metadata_) if self.metadata_ else {}
        }


class AIMetadata(db.Model):
    """Stores metadata about AI operations for traceability and debugging."""
    __tablename__ = "ai_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # property_extraction, recommendation_generation, etc.
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, index=True)
    # Related entity IDs for context
    property_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("properties.id"), nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("customers.id"), nullable=True)
    deal_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("deals.id"), nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tasks.id"), nullable=True)
    # Additional context as JSON
    context_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string

    # Relationships
    property = relationship("Property", foreign_keys=[property_id])
    customer = relationship("Customer", foreign_keys=[customer_id])
    deal = relationship("Deal", foreign_keys=[deal_id])
    task = relationship("Task", foreign_keys=[task_id])

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            "id": self.id,
            "operation_type": self.operation_type,
            "model_name": self.model_name,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "property_id": self.property_id,
            "customer_id": self.customer_id,
            "deal_id": self.deal_id,
            "task_id": self.task_id,
            "context_data": json.loads(self.context_data) if self.context_data else {}
        }


class SyncState(db.Model):
    """Tracks sync run history for the Maskan scraper integration."""
    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_sync_cursor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    properties_synced: Mapped[int] = mapped_column(Integer, default=0)
    properties_created: Mapped[int] = mapped_column(Integer, default=0)
    properties_updated: Mapped[int] = mapped_column(Integer, default=0)
    fields_changed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="idle")  # idle, running, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_cursor": self.last_sync_cursor,
            "properties_synced": self.properties_synced,
            "properties_created": self.properties_created,
            "properties_updated": self.properties_updated,
            "fields_changed": self.fields_changed,
            "status": self.status,
            "error_message": self.error_message,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DashboardStatSnapshot(db.Model):
    """Stores daily snapshots of dashboard metrics for trend calculations."""
    __tablename__ = "dashboard_stat_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, nullable=False)

    # Core dashboard metrics
    total_properties: Mapped[int] = mapped_column(Integer, default=0)
    active_properties: Mapped[int] = mapped_column(Integer, default=0)
    total_agents: Mapped[int] = mapped_column(Integer, default=0)
    total_customers: Mapped[int] = mapped_column(Integer, default=0)
    total_deals: Mapped[int] = mapped_column(Integer, default=0)
    active_deals: Mapped[int] = mapped_column(Integer, default=0)
    total_deal_value: Mapped[int] = mapped_column(BigInteger, default=0)
    active_deal_value: Mapped[int] = mapped_column(BigInteger, default=0)
    avg_property_price: Mapped[int] = mapped_column(Integer, default=0)

    # Optional: counts for recent activities (may be useful for debugging)
    recent_properties_count: Mapped[int] = mapped_column(Integer, default=0)
    recent_deals_count: Mapped[int] = mapped_column(Integer, default=0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "total_properties": self.total_properties,
            "active_properties": self.active_properties,
            "total_agents": self.total_agents,
            "total_customers": self.total_customers,
            "total_deals": self.total_deals,
            "active_deals": self.active_deals,
            "total_deal_value": self.total_deal_value,
            "active_deal_value": self.active_deal_value,
            "avg_property_price": self.avg_property_price,
            "recent_properties_count": self.recent_properties_count,
            "recent_deals_count": self.recent_deals_count,
        }

class ImportBatch(db.Model):
    """CSV import batch metadata (source file not retained long-term)."""

    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)  # customer|property|deal
    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)
    # uploaded -> mapped -> previewed -> reviewing -> executing -> completed|failed
    # rollback_pending -> rolled_back|rollback_partial
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    file_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    uploader_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    uploader_label: Mapped[str] = mapped_column(String(120), default="")
    mapping_json: Mapped[str] = mapped_column(Text, default="{}")
    mode: Mapped[str] = mapped_column(String(32), default="create_only")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    possible_duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, default=0)
    failure_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rollback_status: Mapped[str] = mapped_column(String(32), default="none")
    temp_path: Mapped[str] = mapped_column(String(512), default="")

    rows = relationship("ImportRowResult", back_populates="batch", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "status": self.status,
            "original_filename": self.original_filename,
            "file_hash": self.file_hash,
            "uploader_id": self.uploader_id,
            "mode": self.mode,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "duplicate_rows": self.duplicate_rows,
            "possible_duplicate_rows": self.possible_duplicate_rows,
            "imported_rows": self.imported_rows,
            "skipped_rows": self.skipped_rows,
            "rollback_status": self.rollback_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ImportRowResult(db.Model):
    """Per-row outcome for an import batch (safe diagnostics only)."""

    __tablename__ = "import_row_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(Integer, ForeignKey("import_batches.id"), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # pending|valid|invalid|exact_duplicate|possible_duplicate|imported|skipped|failed|rolled_back
    error_codes: Mapped[str] = mapped_column(String(255), default="")
    diagnostic: Mapped[str] = mapped_column(String(500), default="")  # sanitized, no full PII dump
    match_key: Mapped[str] = mapped_column(String(255), default="")
    created_record_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    decision: Mapped[str] = mapped_column(String(32), default="")  # skip|import| (possible dups)
    decision_by: Mapped[str] = mapped_column(String(120), default="")
    decision_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")  # validated normalized fields only

    batch = relationship("ImportBatch", back_populates="rows")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "row_number": self.row_number,
            "outcome": self.outcome,
            "error_codes": self.error_codes,
            "diagnostic": self.diagnostic,
            "match_key": self.match_key,
            "created_record_id": self.created_record_id,
            "decision": self.decision,
        }


class SavedView(db.Model):
    """User-owned saved list/search filters (allowlisted JSON, never SQL)."""

    __tablename__ = "saved_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    filter_json: Mapped[str] = mapped_column(Text, default="{}")
    sort_spec: Mapped[str] = mapped_column(String(32), default="relevance")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_user_id": self.owner_user_id,
            "name": self.name,
            "entity_scope": self.entity_scope,
            "filter_json": self.filter_json,
            "sort_spec": self.sort_spec,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DealStageHistory(db.Model):
    """Observed deal stage transitions (baseline events are not true history)."""

    __tablename__ = "deal_stage_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("deals.id"), nullable=False, index=True
    )
    from_stage: Mapped[str] = mapped_column(String(50), default="")
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, index=True)
    changed_by: Mapped[str] = mapped_column(String(120), default="")
    event_type: Mapped[str] = mapped_column(
        String(32), default="transition", index=True
    )  # transition|baseline|create
    reason_code: Mapped[str] = mapped_column(String(64), default="")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "deal_id": self.deal_id,
            "from_stage": self.from_stage,
            "to_stage": self.to_stage,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "event_type": self.event_type,
        }


class ForecastSnapshot(db.Model):
    """Period forecast snapshot for later accuracy comparison (no deal PII)."""

    __tablename__ = "forecast_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    weighted_forecast: Mapped[int] = mapped_column(BigInteger, default=0)
    open_pipeline: Mapped[int] = mapped_column(BigInteger, default=0)
    open_count: Mapped[int] = mapped_column(Integer, default=0)
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scope_key": self.scope_key,
            "weighted_forecast": self.weighted_forecast,
            "open_pipeline": self.open_pipeline,
            "open_count": self.open_count,
            "as_of": self.as_of.isoformat() if self.as_of else None,
        }


class CustomerInteraction(db.Model):
    """Manual customer activity (notes/calls/emails/meetings). Bodies not globally searchable."""

    __tablename__ = "customer_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    interaction_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # note|call|email|meeting|other
    subject: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")  # never in global search
    outcome: Mapped[str] = mapped_column(String(64), default="")  # e.g. no_answer|completed
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, index=True)
    follow_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    actor_label: Mapped[str] = mapped_column(String(120), default="")
    related_deal_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("deals.id"), nullable=True
    )
    related_property_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("properties.id"), nullable=True
    )
    follow_up_task_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )
    # immutability: generated events are not stored here; manual only
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual only in this table

    def to_dict(self, *, include_body: bool = True) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "customer_id": self.customer_id,
            "interaction_type": self.interaction_type,
            "subject": self.subject,
            "outcome": self.outcome,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "follow_up_at": self.follow_up_at.isoformat() if self.follow_up_at else None,
            "actor_user_id": self.actor_user_id,
            "actor_label": self.actor_label,
            "related_deal_id": self.related_deal_id,
            "related_property_id": self.related_property_id,
            "follow_up_task_id": self.follow_up_task_id,
            "source": self.source,
            "is_deleted": self.is_deleted,
        }
        if include_body:
            data["body"] = self.body
        return data


class ActivityAuditLog(db.Model):
    """Redacted audit for customer activity (no note bodies / PII values)."""

    __tablename__ = "activity_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actor_label: Mapped[str] = mapped_column(String(120), default="")
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    interaction_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    changed_fields: Mapped[str] = mapped_column(String(255), default="")
    request_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, index=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "actor_user_id": self.actor_user_id,
            "actor_label": self.actor_label,
            "customer_id": self.customer_id,
            "interaction_id": self.interaction_id,
            "action": self.action,
            "changed_fields": self.changed_fields,
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AutomationOutboxEvent(db.Model):
    """Transactional outbox for business events (allowlisted context only)."""

    __tablename__ = "automation_outbox_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(32), nullable=False)
    aggregate_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    actor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), default="")
    changed_fields: Mapped[str] = mapped_column(String(255), default="")  # comma names only
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending|processing|processed|failed|dead
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(String(255), default="")
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AutomationRun(db.Model):
    """Per rule evaluation/action attempt with idempotency key."""

    __tablename__ = "automation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("automation_rules.id"), nullable=True, index=True
    )
    rule_version: Mapped[int] = mapped_column(Integer, default=1)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="matched", index=True
    )  # matched|suppressed|succeeded|failed|skipped
    reason_code: Mapped[str] = mapped_column(String(64), default="")
    action_type: Mapped[str] = mapped_column(String(40), default="")
    action_ref: Mapped[str] = mapped_column(String(120), default="")  # task:id / notif:id
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failure_category: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)


class AutomationSettings(db.Model):
    """Singleton-ish global automation controls (id=1)."""

    __tablename__ = "automation_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    global_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_by: Mapped[str] = mapped_column(String(120), default="")


class Document(db.Model):
    """Secure CRM document metadata (bytes live in private storage, not DB)."""

    __tablename__ = "documents"
    __table_args__ = (
        # logical group + version uniqueness
        # enforced via unique index in migration too
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # customer|property|deal|agent
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    storage_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    media_type: Mapped[str] = mapped_column(String(80), default="")
    byte_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="", index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending_scan", index=True
    )  # pending_scan|available|quarantined|archived|failed
    version: Mapped[int] = mapped_column(Integer, default=1)
    document_group_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    uploaded_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uploaded_by_label: Mapped[str] = mapped_column(String(120), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, index=True)
    archived_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    retention_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scan_engine: Mapped[str] = mapped_column(String(40), default="")
    scan_result: Mapped[str] = mapped_column(String(40), default="")
    metadata_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )

    def to_dict(self) -> Dict[str, Any]:
        """Safe metadata for API/UI — never storage path."""
        return {
            "id": self.id,
            "owner_type": self.owner_type,
            "owner_id": self.owner_id,
            "category": self.category,
            "display_name": self.display_name,
            "media_type": self.media_type,
            "byte_size": self.byte_size,
            "status": self.status,
            "version": self.version,
            "document_group_id": self.document_group_id,
            "is_latest": self.is_latest,
            "uploaded_by_label": self.uploaded_by_label,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "scan_result": self.scan_result,
            # intentionally omit: storage_key, sha256 (not for end users), original_filename optional
        }


class DocumentAuditLog(db.Model):
    """Document access audit — no content, no paths."""

    __tablename__ = "document_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    actor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actor_label: Mapped[str] = mapped_column(String(120), default="")
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(20), default="ok")  # ok|denied|failed
    request_id: Mapped[str] = mapped_column(String(64), default="")
    owner_type: Mapped[str] = mapped_column(String(20), default="")
    category: Mapped[str] = mapped_column(String(40), default="")
    size_band: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, index=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "actor_id": self.actor_id,
            "action": self.action,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VocabTerm(db.Model):
    """Canonical vocabulary term for search synonym expansion (query-side only)."""

    __tablename__ = "vocab_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    lang: Mapped[str] = mapped_column(String(8), default="en")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow_naive, onupdate=_utcnow_naive
    )

    synonyms = relationship("VocabSynonym", back_populates="term", lazy="selectin")


class VocabSynonym(db.Model):
    """Synonym of a vocab term; bidirectional by default."""

    __tablename__ = "vocab_synonyms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vocab_terms.id"), nullable=False, index=True
    )
    synonym_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    bidirectional: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

    term = relationship("VocabTerm", back_populates="synonyms")


class VocabReplacement(db.Model):
    """Directional token replacement applied to queries only (never mutates listings)."""

    __tablename__ = "vocab_replacements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    to_key: Mapped[str] = mapped_column(String(120), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive)

