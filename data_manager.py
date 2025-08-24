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

        # Create sample properties with enhanced data (mix of sale and rental)
        self.add_property("Modern Downtown Condo", "123 Main St, Downtown", 450000, 
                         "Condo", 2, 2, 1200, 
                         "Beautiful modern condo with city views, granite countertops, and hardwood floors", 
                         "active", 1, 2018, 1, 1, 1, "excellent", "Central Air", "Central Air", 
                         None, "Granite Countertops, Hardwood Floors, City Views, Balcony", "Downtown", "residential", "sale")

        self.add_property("Suburban Family Home", "456 Oak Avenue, Suburbia", 650000, 
                         "House", 4, 3, 2800, 
                         "Spacious family home with large backyard, updated kitchen, and 3-car garage", 
                         "active", 1, 2010, 3, 2, 1, "good", "Gas", "Central Air",
                         None, "Updated Kitchen, Large Backyard, 3-Car Garage, Walk-in Closets", "Suburbia", "residential", "sale")

        self.add_property("Luxury Waterfront Estate", "789 Lake Drive, Waterfront", 1250000, 
                         "House", 5, 4, 4500, 
                         "Stunning waterfront estate with private dock, infinity pool, and panoramic lake views", 
                         "active", 1, 2015, 4, 3, 1, "excellent", "Radiant Floor", "Central Air",
                         None, "Private Dock, Infinity Pool, Lake Views, Wine Cellar, Smart Home", "Waterfront", "residential", "sale")

        # Add rental property with Iranian pricing system
        self.add_property("Urban Loft", "321 Industrial Blvd, Arts District", 0, 
                         "Loft", 1, 1, 950, 
                         "Converted industrial loft with exposed brick, high ceilings, and modern amenities", 
                         "active", 2, 1995, 1, 1, 1, "good", "Electric", "Window Units",
                         None, "Exposed Brick, High Ceilings, Industrial Design, Artist Space", "Arts District", "residential", "rental", 400000000, 2500000)

        self.add_property("Starter Home", "654 Pine Street, Neighborhood", 285000, 
                         "House", 3, 2, 1450, 
                         "Perfect starter home with updated appliances, new roof, and fenced yard", 
                         "active", 3, 2005, 2, 1, 1, "good", "Gas", "Central Air",
                         None, "Updated Appliances, New Roof, Fenced Yard, Quiet Street", "Neighborhood", "residential", "sale")

        # Add sample properties
        self.add_property(
            "Modern Downtown Condo", "123 Main St, Downtown", 450000, "Condo",
            2, 2, 1200, "Luxury condo with city views", "active", 1
        )
        self.add_property(
            "Suburban Family Home", "456 Oak Ave, Suburbia", 285000, "House",
            3, 2, 1800, "Perfect for families", "active", 2
        )
        self.add_property(
            "Cozy Starter Home", "789 Pine St, Westside", 195000, "House",
            2, 1, 950, "Great first home", "active", 1
        )
        self.add_property(
            "Luxury Estate", "321 Elite Drive, Hills", 1250000, "House",
            5, 4, 4500, "Premium luxury living", "active", 3
        )
        self.add_property(
            "Investment Duplex", "654 Rental Rd, Midtown", 380000, "Duplex",
            4, 3, 2400, "Great rental income potential", "active", 2
        )

        # Add more properties for better market analysis
        self.add_property(
            "Penthouse Suite", "100 Sky Tower, Downtown", 875000, "Condo",
            3, 3, 2100, "Top floor penthouse with panoramic views", "active", 1
        )
        self.add_property(
            "Victorian Townhouse", "567 Heritage Lane, Historic District", 525000, "Townhouse",
            3, 2.5, 1650, "Restored Victorian with modern amenities", "active", 2
        )
        self.add_property(
            "Ranch Style Home", "890 Country Road, Suburbs", 335000, "House",
            3, 2, 1600, "Single story ranch on large lot", "active", 3
        )
        self.add_property(
            "Urban Loft", "45 Industrial Way, Arts District", 395000, "Loft",
            1, 1, 1100, "Converted warehouse loft with exposed brick", "active", 1
        )
        self.add_property(
            "Garden Apartment", "234 Green Street, Westside", 275000, "Condo",
            2, 1.5, 980, "Ground floor with private garden", "active", 2
        )
        self.add_property(
            "Executive Home", "777 Executive Circle, Uptown", 695000, "House",
            4, 3.5, 2800, "Executive home in gated community", "active", 3
        )
        self.add_property(
            "Beachfront Condo", "888 Ocean View, Coastal", 620000, "Condo",
            2, 2, 1350, "Direct beach access with ocean views", "active", 1
        )
        self.add_property(
            "Affordable Starter", "999 Budget Lane, Eastside", 165000, "House",
            2, 1, 850, "Perfect for first-time buyers", "active", 2
        )
        self.add_property(
            "Commercial Space", "1010 Business Blvd, Commercial District", 850000, "Commercial",
            0, 2, 3500, "Prime retail/office space", "active", 3
        )
        self.add_property(
            "Family Estate", "1111 Family Way, Prestigious", 925000, "House",
            5, 4, 3200, "Large family home with pool", "active", 1
        )


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
                    status: str = "active", agent_id: Optional[int] = None,
                    year_built: int = None, parking_spaces: int = 0, 
                    floors: int = 1, units: int = 1, property_condition: str = "good",
                    heating_type: str = "", cooling_type: str = "", 
                    rental_price: float = None, property_features: str = "",
                    neighborhood: str = "", property_category: str = "residential",
                    listing_type: str = "sale", rahn: float = None, ejare: float = None) -> Property:
        property_obj = Property(self.next_property_id, title, address, price, property_type, 
                               bedrooms, bathrooms, square_feet, description, status, agent_id,
                               year_built, parking_spaces, floors, units, property_condition,
                               heating_type, cooling_type, rental_price, property_features,
                               neighborhood, property_category, listing_type, rahn, ejare)
        self.properties[self.next_property_id] = property_obj
        self.next_property_id += 1

        # Update agent's active listings count
        if agent_id and agent_id in self.agents:
            self.agents[agent_id].active_listings += 1

        return property_obj

    def get_properties(self, status: Optional[str] = None, search: str = "", 
                      property_type: str = "", min_price: float = None, max_price: float = None,
                      bedrooms: int = None, bathrooms: int = None, min_sqft: int = None,
                      max_sqft: int = None, neighborhood: str = "", property_condition: str = "",
                      property_category: str = "", year_built_min: int = None, year_built_max: int = None,
                      agent_id: int = None) -> List[Property]:
        properties = list(self.properties.values())

        # Apply filters
        if status:
            properties = [p for p in properties if p.status == status]

        if search:
            search_lower = search.lower()
            properties = [p for p in properties if 
                         search_lower in p.title.lower() or 
                         search_lower in p.address.lower() or 
                         search_lower in p.description.lower()]

        if property_type:
            properties = [p for p in properties if p.property_type.lower() == property_type.lower()]

        if min_price is not None:
            properties = [p for p in properties if p.price >= min_price]

        if max_price is not None:
            properties = [p for p in properties if p.price <= max_price]

        if bedrooms is not None:
            properties = [p for p in properties if p.bedrooms >= bedrooms]

        if bathrooms is not None:
            properties = [p for p in properties if p.bathrooms >= bathrooms]

        if min_sqft is not None:
            properties = [p for p in properties if p.square_feet >= min_sqft]

        if max_sqft is not None:
            properties = [p for p in properties if p.square_feet <= max_sqft]

        if neighborhood:
            properties = [p for p in properties if neighborhood.lower() in p.neighborhood.lower()]

        if property_condition:
            properties = [p for p in properties if p.property_condition.lower() == property_condition.lower()]

        if property_category:
            properties = [p for p in properties if p.property_category.lower() == property_category.lower()]

        if year_built_min is not None:
            properties = [p for p in properties if p.year_built and p.year_built >= year_built_min]

        if year_built_max is not None:
            properties = [p for p in properties if p.year_built and p.year_built <= year_built_max]

        if agent_id is not None:
            properties = [p for p in properties if p.agent_id == agent_id]

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