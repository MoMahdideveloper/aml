from typing import Dict, List, Optional
from models import Property, Agent, Customer, Deal, Task
from datetime import datetime, timedelta
import logging

class DataManager:
    def __init__(self):
        self.properties: Dict[int, Property] = {}
        self.agents: Dict[int, Agent] = {}
        self.customers: Dict[int, Customer] = {}
        self.deals: Dict[int, Deal] = {}
        self.tasks: Dict[int, Task] = {}
        
        # Auto-increment IDs
        self.next_property_id = 1
        self.next_agent_id = 1
        self.next_customer_id = 1
        self.next_deal_id = 1
        self.next_task_id = 1
        
        # Initialize with sample data
        self._initialize_data()

    def _initialize_data(self):
        """Initialize the system with sample data"""
        # Create sample agents
        self.add_agent("Sarah Johnson", "sarah.johnson@realestate.com", "+1-555-0101", 
                      "Luxury Homes", "Specializing in high-end residential properties with 10+ years experience")
        self.add_agent("Mike Chen", "mike.chen@realestate.com", "+1-555-0102", 
                      "Commercial Properties", "Expert in commercial real estate and investment properties")
        self.add_agent("Lisa Rodriguez", "lisa.rodriguez@realestate.com", "+1-555-0103", 
                      "First-Time Buyers", "Dedicated to helping first-time homebuyers navigate the market")

        # Create sample properties
        self.add_property("Modern Downtown Condo", "123 Main St, Downtown", 450000, 
                         "Condo", 2, 2, 1200, 
                         "Beautiful modern condo with city views, granite countertops, and hardwood floors", 
                         "active", 1)
        
        self.add_property("Suburban Family Home", "456 Oak Avenue, Suburbia", 650000, 
                         "House", 4, 3, 2800, 
                         "Spacious family home with large backyard, updated kitchen, and 3-car garage", 
                         "active", 1)
        
        self.add_property("Luxury Waterfront Estate", "789 Lake Drive, Waterfront", 1250000, 
                         "House", 5, 4, 4500, 
                         "Stunning waterfront estate with private dock, infinity pool, and panoramic lake views", 
                         "active", 1)
        
        self.add_property("Urban Loft", "321 Industrial Blvd, Arts District", 380000, 
                         "Loft", 1, 1, 950, 
                         "Converted industrial loft with exposed brick, high ceilings, and modern amenities", 
                         "active", 2)
        
        self.add_property("Starter Home", "654 Pine Street, Neighborhood", 285000, 
                         "House", 3, 2, 1450, 
                         "Perfect starter home with updated appliances, new roof, and fenced yard", 
                         "active", 3)

        # Create sample customers
        self.add_customer("John Smith", "john.smith@email.com", "+1-555-1001", 
                         400000, 500000, 2, 2, "Condo", "Downtown")
        
        self.add_customer("Emily Davis", "emily.davis@email.com", "+1-555-1002", 
                         600000, 750000, 3, 2, "House", "Suburbia")
        
        self.add_customer("Robert Wilson", "robert.wilson@email.com", "+1-555-1003", 
                         1000000, 1500000, 4, 3, "House", "Waterfront")
        
        self.add_customer("Maria Garcia", "maria.garcia@email.com", "+1-555-1004", 
                         250000, 350000, 2, 1, "Any", "Any")

        # Create sample deals
        self.add_deal(1, 1, 1, "qualified", 440000)  # John interested in downtown condo
        self.add_deal(2, 2, 1, "proposal", 630000)   # Emily looking at suburban home
        self.add_deal(3, 3, 1, "negotiation", 1200000)  # Robert negotiating on waterfront estate

        # Create sample tasks
        self.add_task("Follow up with John Smith", "Call John about condo viewing feedback", 1, "high", 
                     datetime.now() + timedelta(days=1))
        self.add_task("Prepare property report", "Create detailed report for waterfront estate", 1, "medium", 
                     datetime.now() + timedelta(days=3))
        self.add_task("Schedule home inspection", "Coordinate inspection for Pine Street property", 3, "high", 
                     datetime.now() + timedelta(days=2))

    # Property methods
    def add_property(self, title: str, address: str, price: float, property_type: str, 
                    bedrooms: int, bathrooms: int, square_feet: int, description: str, 
                    status: str = "active", agent_id: Optional[int] = None) -> Property:
        property_obj = Property(self.next_property_id, title, address, price, property_type, 
                               bedrooms, bathrooms, square_feet, description, status, agent_id)
        self.properties[self.next_property_id] = property_obj
        self.next_property_id += 1
        
        # Update agent's active listings count
        if agent_id and agent_id in self.agents:
            self.agents[agent_id].active_listings += 1
        
        return property_obj

    def get_properties(self, status: Optional[str] = None) -> List[Property]:
        properties = list(self.properties.values())
        if status:
            properties = [p for p in properties if p.status == status]
        return properties

    def get_property(self, property_id: int) -> Optional[Property]:
        return self.properties.get(property_id)

    def update_property(self, property_id: int, **kwargs) -> Optional[Property]:
        if property_id in self.properties:
            property_obj = self.properties[property_id]
            for key, value in kwargs.items():
                if hasattr(property_obj, key):
                    setattr(property_obj, key, value)
            property_obj.updated_at = datetime.now()
            return property_obj
        return None

    # Agent methods
    def add_agent(self, name: str, email: str, phone: str, specialization: str = "", bio: str = "") -> Agent:
        agent = Agent(self.next_agent_id, name, email, phone, specialization, bio)
        self.agents[self.next_agent_id] = agent
        self.next_agent_id += 1
        return agent

    def get_agents(self) -> List[Agent]:
        return list(self.agents.values())

    def get_agent(self, agent_id: int) -> Optional[Agent]:
        return self.agents.get(agent_id)

    # Customer methods
    def add_customer(self, name: str, email: str, phone: str, budget_min: float = 0, 
                    budget_max: float = 0, preferred_bedrooms: int = 0, 
                    preferred_bathrooms: int = 0, preferred_type: str = "", 
                    location_preference: str = "") -> Customer:
        customer = Customer(self.next_customer_id, name, email, phone, budget_min, 
                           budget_max, preferred_bedrooms, preferred_bathrooms, 
                           preferred_type, location_preference)
        self.customers[self.next_customer_id] = customer
        self.next_customer_id += 1
        return customer

    def get_customers(self) -> List[Customer]:
        return list(self.customers.values())

    def get_customer(self, customer_id: int) -> Optional[Customer]:
        return self.customers.get(customer_id)

    # Deal methods
    def add_deal(self, property_id: int, customer_id: int, agent_id: int, 
                status: str = "prospecting", offer_amount: float = 0) -> Deal:
        deal = Deal(self.next_deal_id, property_id, customer_id, agent_id, status, offer_amount)
        self.deals[self.next_deal_id] = deal
        self.next_deal_id += 1
        return deal

    def get_deals(self, agent_id: Optional[int] = None) -> List[Deal]:
        deals = list(self.deals.values())
        if agent_id:
            deals = [d for d in deals if d.agent_id == agent_id]
        return deals

    def get_deal(self, deal_id: int) -> Optional[Deal]:
        return self.deals.get(deal_id)

    def update_deal(self, deal_id: int, **kwargs) -> Optional[Deal]:
        if deal_id in self.deals:
            deal = self.deals[deal_id]
            for key, value in kwargs.items():
                if hasattr(deal, key):
                    setattr(deal, key, value)
            deal.updated_at = datetime.now()
            return deal
        return None

    # Task methods
    def add_task(self, title: str, description: str, agent_id: int, priority: str = "medium", 
                due_date: Optional[datetime] = None) -> Task:
        task = Task(self.next_task_id, title, description, agent_id, priority, "pending", due_date)
        self.tasks[self.next_task_id] = task
        self.next_task_id += 1
        return task

    def get_tasks(self, agent_id: Optional[int] = None, status: Optional[str] = None) -> List[Task]:
        tasks = list(self.tasks.values())
        if agent_id:
            tasks = [t for t in tasks if t.agent_id == agent_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def get_task(self, task_id: int) -> Optional[Task]:
        return self.tasks.get(task_id)

    def complete_task(self, task_id: int) -> Optional[Task]:
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "completed"
            task.completed_at = datetime.now()
            return task
        return None

    # Analytics methods
    def get_dashboard_stats(self) -> Dict:
        total_properties = len(self.properties)
        active_properties = len([p for p in self.properties.values() if p.status == "active"])
        total_customers = len(self.customers)
        total_deals = len(self.deals)
        active_deals = len([d for d in self.deals.values() if d.status not in ["closed_won", "closed_lost"]])
        
        # Calculate total deal value
        total_deal_value = sum(deal.offer_amount for deal in self.deals.values() if deal.offer_amount > 0)
        
        return {
            'total_properties': total_properties,
            'active_properties': active_properties,
            'total_customers': total_customers,
            'total_deals': total_deals,
            'active_deals': active_deals,
            'total_deal_value': total_deal_value
        }

# Global data manager instance
data_manager = DataManager()
