from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import db

class Property(db.Model):
    __tablename__ = 'properties'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Float, default=0)
    property_type: Mapped[str] = mapped_column(String(50), nullable=False)
    bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    bathrooms: Mapped[int] = mapped_column(Integer, default=0)
    square_feet: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(20), default='active')
    
    # Enhanced fields
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parking_spaces: Mapped[int] = mapped_column(Integer, default=0)
    floors: Mapped[int] = mapped_column(Integer, default=1)
    units: Mapped[int] = mapped_column(Integer, default=1)
    property_condition: Mapped[str] = mapped_column(String(50), default='good')
    heating_type: Mapped[str] = mapped_column(String(50), default='')
    cooling_type: Mapped[str] = mapped_column(String(50), default='')
    rental_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    property_features: Mapped[str] = mapped_column(Text, default='')
    neighborhood: Mapped[str] = mapped_column(String(100), default='')
    property_category: Mapped[str] = mapped_column(String(50), default='residential')
    
    # Iranian real estate pricing system
    listing_type: Mapped[str] = mapped_column(String(20), default='sale')
    rahn: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Deposit for rentals
    ejare: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Monthly rent
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('agents.id'), nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="properties")
    deals = relationship("Deal", back_populates="property")
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'address': self.address,
            'price': self.price,
            'property_type': self.property_type,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'square_feet': self.square_feet,
            'description': self.description,
            'status': self.status,
            'agent_id': self.agent_id,
            'year_built': self.year_built,
            'parking_spaces': self.parking_spaces,
            'floors': self.floors,
            'units': self.units,
            'property_condition': self.property_condition,
            'heating_type': self.heating_type,
            'cooling_type': self.cooling_type,
            'rental_price': self.rental_price,
            'property_features': self.property_features,
            'neighborhood': self.neighborhood,
            'property_category': self.property_category,
            'listing_type': self.listing_type,
            'rahn': self.rahn,
            'ejare': self.ejare,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
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
            return [feature.strip() for feature in self.property_features.split(',')]
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

class Agent(db.Model):
    __tablename__ = 'agents'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    specialization: Mapped[str] = mapped_column(String(255), default='')
    bio: Mapped[str] = mapped_column(Text, default='')
    total_sales: Mapped[int] = mapped_column(Integer, default=0)
    active_listings: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    properties = relationship("Property", back_populates="agent")
    deals = relationship("Deal", back_populates="agent")
    tasks = relationship("Task", back_populates="agent")
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'specialization': self.specialization,
            'bio': self.bio,
            'created_at': self.created_at.isoformat(),
            'total_sales': self.total_sales,
            'active_listings': self.active_listings
        }

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    budget_min: Mapped[float] = mapped_column(Float, default=0)
    budget_max: Mapped[float] = mapped_column(Float, default=0)
    preferred_bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    preferred_bathrooms: Mapped[int] = mapped_column(Integer, default=0)
    preferred_type: Mapped[str] = mapped_column(String(50), default='')
    location_preference: Mapped[str] = mapped_column(String(255), default='')
    status: Mapped[str] = mapped_column(String(20), default='active')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    deals = relationship("Deal", back_populates="customer")
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'budget_min': self.budget_min,
            'budget_max': self.budget_max,
            'preferred_bedrooms': self.preferred_bedrooms,
            'preferred_bathrooms': self.preferred_bathrooms,
            'preferred_type': self.preferred_type,
            'location_preference': self.location_preference,
            'created_at': self.created_at.isoformat(),
            'status': self.status
        }

class Deal(db.Model):
    __tablename__ = 'deals'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(50), default='prospecting')
    offer_amount: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey('properties.id'), nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey('customers.id'), nullable=False)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey('agents.id'), nullable=False)
    
    # Relationships
    property = relationship("Property", back_populates="deals")
    customer = relationship("Customer", back_populates="deals")
    agent = relationship("Agent", back_populates="deals")
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'property_id': self.property_id,
            'customer_id': self.customer_id,
            'agent_id': self.agent_id,
            'status': self.status,
            'offer_amount': self.offer_amount,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'notes': self.notes
        }

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='')
    priority: Mapped[str] = mapped_column(String(20), default='medium')
    status: Mapped[str] = mapped_column(String(20), default='pending')
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Foreign Keys
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey('agents.id'), nullable=False)
    
    # Relationships
    agent = relationship("Agent", back_populates="tasks")
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'agent_id': self.agent_id,
            'priority': self.priority,
            'status': self.status,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }