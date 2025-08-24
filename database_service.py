"""
Database service to replace the in-memory DataManager with SQLAlchemy operations
"""
from typing import Dict, List, Optional
from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.orm import sessionmaker
from database import db
from sqlalchemy_models import Property, Agent, Customer, Deal, Task
from datetime import datetime, timedelta
import logging

class DatabaseService:
    """Service class to handle database operations for all entities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    # Property operations
    def add_property(self, title: str, address: str, price: float, property_type: str,
                    bedrooms: int, bathrooms: int, square_feet: int, description: str,
                    status: str = "active", agent_id: Optional[int] = None,
                    year_built: Optional[int] = None, parking_spaces: int = 0,
                    floors: int = 1, units: int = 1, property_condition: str = "good",
                    heating_type: str = "", cooling_type: str = "",
                    rental_price: Optional[float] = None, property_features: str = "",
                    neighborhood: str = "", property_category: str = "residential",
                    listing_type: str = "sale", rahn: Optional[float] = None,
                    ejare: Optional[float] = None) -> Property:
        """Add a new property to the database"""
        property_obj = Property(
            title=title, address=address, price=price, property_type=property_type,
            bedrooms=bedrooms, bathrooms=bathrooms, square_feet=square_feet,
            description=description, status=status, agent_id=agent_id,
            year_built=year_built, parking_spaces=parking_spaces, floors=floors,
            units=units, property_condition=property_condition,
            heating_type=heating_type, cooling_type=cooling_type,
            rental_price=rental_price, property_features=property_features,
            neighborhood=neighborhood, property_category=property_category,
            listing_type=listing_type, rahn=rahn, ejare=ejare
        )
        db.session.add(property_obj)
        db.session.commit()
        return property_obj
    
    def get_properties(self, search: str = "", property_type: str = "",
                      property_category: str = "", property_condition: str = "",
                      neighborhood: str = "", min_price: Optional[float] = None,
                      max_price: Optional[float] = None, bedrooms: Optional[int] = None,
                      bathrooms: Optional[int] = None, min_sqft: Optional[int] = None,
                      max_sqft: Optional[int] = None, year_built_min: Optional[int] = None,
                      year_built_max: Optional[int] = None, agent_id: Optional[int] = None) -> List[Property]:
        """Get properties with optional filtering"""
        query = Property.query
        
        if search:
            query = query.filter(or_(
                Property.title.ilike(f'%{search}%'),
                Property.address.ilike(f'%{search}%'),
                Property.description.ilike(f'%{search}%')
            ))
        
        if property_type:
            query = query.filter(Property.property_type == property_type)
        if property_category:
            query = query.filter(Property.property_category == property_category)
        if property_condition:
            query = query.filter(Property.property_condition == property_condition)
        if neighborhood:
            query = query.filter(Property.neighborhood == neighborhood)
        if min_price is not None:
            query = query.filter(Property.price >= min_price)
        if max_price is not None:
            query = query.filter(Property.price <= max_price)
        if bedrooms is not None:
            query = query.filter(Property.bedrooms >= bedrooms)
        if bathrooms is not None:
            query = query.filter(Property.bathrooms >= bathrooms)
        if min_sqft is not None:
            query = query.filter(Property.square_feet >= min_sqft)
        if max_sqft is not None:
            query = query.filter(Property.square_feet <= max_sqft)
        if year_built_min is not None:
            query = query.filter(Property.year_built >= year_built_min)
        if year_built_max is not None:
            query = query.filter(Property.year_built <= year_built_max)
        if agent_id is not None:
            query = query.filter(Property.agent_id == agent_id)
        
        return query.order_by(desc(Property.created_at)).all()
    
    def get_property(self, property_id: int) -> Optional[Property]:
        """Get a property by ID"""
        return Property.query.get(property_id)
    
    def update_property(self, property_id: int, **kwargs) -> Optional[Property]:
        """Update a property"""
        property_obj = Property.query.get(property_id)
        if property_obj:
            for key, value in kwargs.items():
                if hasattr(property_obj, key):
                    setattr(property_obj, key, value)
            property_obj.updated_at = datetime.utcnow()
            db.session.commit()
        return property_obj
    
    def delete_property(self, property_id: int) -> bool:
        """Delete a property"""
        property_obj = Property.query.get(property_id)
        if property_obj:
            db.session.delete(property_obj)
            db.session.commit()
            return True
        return False
    
    def update_deal(self, deal_id: int, **kwargs) -> Optional[Deal]:
        """Update a deal"""
        deal = Deal.query.get(deal_id)
        if deal:
            for key, value in kwargs.items():
                if hasattr(deal, key):
                    setattr(deal, key, value)
            deal.updated_at = datetime.utcnow()
            db.session.commit()
        return deal
    
    # Agent operations
    def add_agent(self, name: str, email: str, phone: str,
                 specialization: str = "", bio: str = "") -> Agent:
        """Add a new agent"""
        agent = Agent(name=name, email=email, phone=phone,
                     specialization=specialization, bio=bio)
        db.session.add(agent)
        db.session.commit()
        return agent
    
    def get_agents(self) -> List[Agent]:
        """Get all agents"""
        return Agent.query.order_by(Agent.name).all()
    
    def get_agent(self, agent_id: int) -> Optional[Agent]:
        """Get an agent by ID"""
        return Agent.query.get(agent_id)
    
    # Customer operations
    def add_customer(self, name: str, email: str, phone: str,
                    budget_min: float = 0, budget_max: float = 0,
                    preferred_bedrooms: int = 0, preferred_bathrooms: int = 0,
                    preferred_type: str = "", location_preference: str = "") -> Customer:
        """Add a new customer"""
        customer = Customer(
            name=name, email=email, phone=phone, budget_min=budget_min,
            budget_max=budget_max, preferred_bedrooms=preferred_bedrooms,
            preferred_bathrooms=preferred_bathrooms, preferred_type=preferred_type,
            location_preference=location_preference
        )
        db.session.add(customer)
        db.session.commit()
        return customer
    
    def get_customers(self) -> List[Customer]:
        """Get all customers"""
        return Customer.query.order_by(Customer.name).all()
    
    def get_customer(self, customer_id: int) -> Optional[Customer]:
        """Get a customer by ID"""
        return Customer.query.get(customer_id)
    
    # Deal operations
    def add_deal(self, property_id: int, customer_id: int, agent_id: int,
                status: str = "prospecting", offer_amount: float = 0) -> Deal:
        """Add a new deal"""
        deal = Deal(property_id=property_id, customer_id=customer_id,
                   agent_id=agent_id, status=status, offer_amount=offer_amount)
        db.session.add(deal)
        db.session.commit()
        return deal
    
    def get_deals(self) -> List[Deal]:
        """Get all deals"""
        return Deal.query.order_by(desc(Deal.created_at)).all()
    
    def get_deal(self, deal_id: int) -> Optional[Deal]:
        """Get a deal by ID"""
        return Deal.query.get(deal_id)
    
    # Task operations
    def add_task(self, title: str, description: str, agent_id: int,
                priority: str = "medium", status: str = "pending",
                due_date: Optional[datetime] = None) -> Task:
        """Add a new task"""
        task = Task(title=title, description=description, agent_id=agent_id,
                   priority=priority, status=status, due_date=due_date)
        db.session.add(task)
        db.session.commit()
        return task
    
    def get_tasks(self, agent_id: Optional[int] = None, status: Optional[str] = None) -> List[Task]:
        """Get tasks with optional filtering"""
        query = Task.query
        
        if agent_id:
            query = query.filter(Task.agent_id == agent_id)
        if status:
            query = query.filter(Task.status == status)
        
        return query.order_by(desc(Task.created_at)).all()
    
    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a task by ID"""
        return Task.query.get(task_id)
    
    def complete_task(self, task_id: int) -> Optional[Task]:
        """Mark a task as completed"""
        task = Task.query.get(task_id)
        if task:
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            db.session.commit()
        return task
    
    # Dashboard statistics
    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        total_properties = Property.query.count()
        active_properties = Property.query.filter(Property.status == 'active').count()
        total_agents = Agent.query.count()
        total_customers = Customer.query.count()
        total_deals = Deal.query.count()
        active_deals = Deal.query.filter(Deal.status.in_(['prospecting', 'qualified', 'proposal', 'negotiation'])).count()
        
        # Calculate deal values
        total_deal_value = db.session.query(func.sum(Deal.offer_amount)).scalar() or 0
        active_deal_value = db.session.query(func.sum(Deal.offer_amount)).filter(
            Deal.status.in_(['prospecting', 'qualified', 'proposal', 'negotiation'])
        ).scalar() or 0
        
        # Recent activities
        recent_properties = Property.query.order_by(desc(Property.created_at)).limit(5).all()
        recent_deals = Deal.query.order_by(desc(Deal.created_at)).limit(5).all()
        
        # Calculate average property price
        avg_property_price = db.session.query(func.avg(Property.price)).filter(Property.price > 0).scalar() or 0
        
        return {
            'total_properties': total_properties,
            'active_properties': active_properties,
            'total_agents': total_agents,
            'total_customers': total_customers,
            'total_deals': total_deals,
            'active_deals': active_deals,
            'total_deal_value': total_deal_value,
            'active_deal_value': active_deal_value,
            'avg_property_price': avg_property_price,
            'recent_properties': recent_properties,
            'recent_deals': recent_deals
        }

# Global database service instance
database_service = DatabaseService()