"""
Database service to replace the in-memory DataManager with SQLAlchemy operations
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import desc, func, or_
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import selectinload

from database import db
from repositories import CustomerRepository, PropertyRepository, DashboardStatisticsRepository
from sqlalchemy_models import Agent, Customer, Deal, Property, Task, PropertyAIHistory, User, PropertyActivityLog
from database_transaction_manager import with_transaction, safe_database_operation, database_transaction
from utils.execution_tracer import log_execution


class DatabaseService:
    """Service class to handle database operations for all entities"""

    def __init__(self):
        self.logger = logging.getLogger("services.database_service")
        self.property_repository = PropertyRepository()
        self.customer_repository = CustomerRepository()
        self.dashboard_statistics_repository = DashboardStatisticsRepository()

    @staticmethod
    @log_execution
    def _to_toman_int(value, default: int = 0) -> int:
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return default
        return int(round(float(value)))

    @staticmethod
    @log_execution
    def _supports_soft_delete(entity) -> bool:
        """Return True only for mapped models with is_deleted/deleted_at columns."""
        if entity is None:
            return False
        try:
            mapper = sa_inspect(entity.__class__)
            return "is_deleted" in mapper.columns and "deleted_at" in mapper.columns
        except Exception:
            return False

    @staticmethod
    @log_execution
    def _is_deleted(entity) -> bool:
        if not DatabaseService._supports_soft_delete(entity):
            return False
        return getattr(entity, "is_deleted", False) is True

    @log_execution
    def _invalidate_market_cache(self) -> None:
        try:
            from extensions import cache

            cache.delete("market_analysis:v1")
        except Exception as exc:
            self.logger.debug("Market cache invalidation skipped: %s", exc)

    @log_execution
    def _invalidate_property_caches(self, property_id: int) -> None:
        self._invalidate_market_cache()
        try:
            from services.gemini_service import gemini_service

            gemini_service.bump_entity_cache_version("property", property_id)
        except Exception as exc:
            self.logger.debug("Property cache invalidation skipped for %s: %s", property_id, exc)

    @log_execution
    def _invalidate_customer_caches(self, customer_id: int) -> None:
        self._invalidate_market_cache()
        try:
            from services.gemini_service import gemini_service

            gemini_service.bump_entity_cache_version("customer", customer_id)
        except Exception as exc:
            self.logger.debug("Customer cache invalidation skipped for %s: %s", customer_id, exc)

    # Property operations
    @log_execution
    def add_property(
        self,
        title: str,
        address: str,
        price: int,
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
        rental_price: Optional[int] = None,
        property_features: str = "",
        neighborhood: str = "",
        property_category: str = "residential",
        listing_type: str = "sale",
        rahn: Optional[int] = None,
        ejare: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        image_filename: Optional[str] = None,
        **kwargs
    ) -> Property:
        """Backward-compatible wrapper that delegates to create_property_with_validation."""
        property_obj = self.create_property_with_validation(
            title=title,
            address=address,
            price=price,
            property_type=property_type,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            square_feet=square_feet,
            description=description,
            status=status,
            agent_id=agent_id,
            year_built=year_built,
            parking_spaces=parking_spaces,
            floors=floors,
            units=units,
            property_condition=property_condition,
            heating_type=heating_type,
            cooling_type=cooling_type,
            rental_price=rental_price,
            neighborhood=neighborhood,
            property_category=property_category,
            listing_type=listing_type,
            rahn=rahn,
            ejare=ejare,
            property_features=property_features,
            latitude=latitude,
            longitude=longitude,
            image_filename=image_filename,
            **kwargs
        )
        return property_obj

    @log_execution
    def get_properties(
        self,
        search: str = "",
        property_type: str = "",
        property_category: str = "",
        property_condition: str = "",
        neighborhood: str = "",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        bedrooms: Optional[int] = None,
        bathrooms: Optional[int] = None,
        min_sqft: Optional[int] = None,
        max_sqft: Optional[int] = None,
        year_built_min: Optional[int] = None,
        year_built_max: Optional[int] = None,
        agent_id: Optional[int] = None,
        status: Optional[str] = None,
        listing_type: str = "",
    ) -> List[Property]:
        """Get properties with optional filtering"""
        return self.property_repository.list_filtered(
            search=search,
            property_type=property_type,
            property_category=property_category,
            property_condition=property_condition,
            neighborhood=neighborhood,
            min_price=min_price,
            max_price=max_price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            min_sqft=min_sqft,
            max_sqft=max_sqft,
            year_built_min=year_built_min,
            year_built_max=year_built_max,
            agent_id=agent_id,
            status=status,
            listing_type=listing_type,
        )

    @log_execution
    def get_property(self, property_id: int) -> Optional[Property]:
        """Get a property by ID with basic error handling"""
        try:
            return self.property_repository.get_by_id(property_id)
        except Exception as e:
            self.logger.error(
                "Error fetching property",
                extra={
                    "property_id": property_id,
                    "error": str(e),
                    "operation": "get_property"
                }
            )
            db.session.rollback()
            return None
    
    @log_execution
    def get_property_with_validation(self, property_id: int) -> Optional[Property]:
        """Get a property by ID with comprehensive validation and error handling"""
        if not isinstance(property_id, int) or property_id <= 0:
            self.logger.warning(
                "Invalid property ID provided",
                extra={
                    "property_id": property_id,
                    "operation": "get_property_with_validation",
                    "validation_step": "id_validation"
                }
            )
            return None

        try:
            property_obj = self.property_repository.get_by_id(property_id)
            if property_obj:
                # Validate property data integrity
                if not property_obj.title or not property_obj.address:
                    self.logger.warning(
                        "Property has incomplete data",
                        extra={
                            "property_id": property_id,
                            "operation": "get_property_with_validation",
                            "validation_step": "data_integrity",
                            "missing_fields": [
                                field for field in ["title", "address"]
                                if not getattr(property_obj, field, None)
                            ]
                        }
                    )
                    # Still return the property but log the issue

                # Ensure agent relationship is loaded if it exists
                if property_obj.agent_id and not property_obj.agent:
                    self.logger.warning(
                        "Property has agent_id but no agent relationship",
                        extra={
                            "property_id": property_id,
                            "operation": "get_property_with_validation",
                            "validation_step": "relationship_loading",
                            "agent_id": property_obj.agent_id
                        }
                    )

            return property_obj

        except Exception as e:
            self.logger.error(
                "Database error fetching property",
                extra={
                    "property_id": property_id,
                    "operation": "get_property_with_validation",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            db.session.rollback()
            return None
    
    @log_execution
    def get_related_properties(self, property_id: int, limit: int = 4) -> List[Property]:
        """Get related properties with error handling and fallback logic"""
        try:
            # First get the main property to determine criteria
            main_property = self.get_property(property_id)
            if not main_property:
                return []
            
            # Build query for related properties
            query = Property.query.filter(
                Property.id != property_id,
                Property.is_deleted.is_(False),
            )
            
            # Add filters based on available data
            filters = []
            if main_property.neighborhood:
                filters.append(Property.neighborhood == main_property.neighborhood)
            if main_property.property_type:
                filters.append(Property.property_type == main_property.property_type)
            if main_property.property_category:
                filters.append(Property.property_category == main_property.property_category)
            
            if filters:
                # Use OR condition to find properties matching any criteria
                from sqlalchemy import or_
                query = query.filter(or_(*filters))
            
            # Load agent relationships and limit results
            related_properties = query.options(selectinload(Property.agent)).limit(limit).all()
            
            # Add agent names safely
            for prop in related_properties:
                if hasattr(prop, 'agent') and prop.agent:
                    setattr(prop, "agent_name", prop.agent.name)
                else:
                    setattr(prop, "agent_name", "Unassigned")
            
            return related_properties
            
        except Exception as e:
            self.logger.warning(
                "Error fetching related properties",
                extra={
                    "property_id": property_id,
                    "limit": limit,
                    "operation": "get_related_properties",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            return []  # Return empty list rather than failing
    
    @log_execution
    def validate_property_access(self, property_id: int, user_id: Optional[int] = None) -> bool:
        """Validate if user has access to the property based on their role and relationship to the property."""
        try:
            # If no user ID provided, deny access
            if user_id is None:
                return False

            # Get the user
            user = db.session.get(User, user_id)
            if not user:
                return False

            # Get the property
            property_obj = self.get_property(property_id)
            if not property_obj:
                return False

            # Admin can access any property
            if user.role == "admin":
                return True

            # Agent can access only properties they are assigned to
            if user.role == "agent":
                return property_obj.agent_id == user_id

            # For other roles (e.g., viewer), we might allow viewing active properties only
            # For now, we'll deny access to non-admin/non-agent users
            return False
        except Exception as e:
            self.logger.error(f"Error validating property access for property {property_id} and user {user_id}: {str(e)}")
            return False

    @log_execution
    def update_property(self, property_id: int, **kwargs) -> Optional[Property]:
        """Backward-compatible wrapper that delegates to update_property_with_validation."""
        return self.update_property_with_validation(property_id, **kwargs)

    @log_execution
    def delete_property(self, property_id: int) -> bool:
        """Backward-compatible wrapper that delegates to delete_property_with_validation."""
        try:
            return self.delete_property_with_validation(property_id)
        except ValueError:
            return False
    
    @with_transaction()
    @log_execution
    def create_property_with_validation(
        self,
        title: str,
        address: str,
        price: int,
        property_type: str,
        bedrooms: int = 0,
        bathrooms: int = 0,
        square_feet: int = 0,
        description: str = "",
        status: str = "active",
        agent_id: Optional[int] = None,
        year_built: Optional[int] = None,
        parking_spaces: int = 0,
        floors: int = 1,
        units: int = 1,
        property_condition: str = "good",
        heating_type: str = "",
        cooling_type: str = "",
        rental_price: Optional[int] = None,
        neighborhood: str = "",
        property_category: str = "residential",
        listing_type: str = "sale",
        rahn: Optional[int] = None,
        ejare: Optional[int] = None,
        property_features: str = "",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        image_filename: Optional[str] = None,
        **kwargs
    ) -> Property:
        """Create a new property with comprehensive validation and transaction management"""
        
        # Validate required fields
        if not title or not title.strip():
            raise ValueError("Property title is required")
        if not address or not address.strip():
            raise ValueError("Property address is required")
        if not property_type or not property_type.strip():
            raise ValueError("Property type is required")
        
        # Validate numeric fields
        price = self._to_toman_int(price)
        rental_price = self._to_toman_int(rental_price, default=0) if rental_price is not None else None
        rahn = self._to_toman_int(rahn, default=0) if rahn is not None else None
        ejare = self._to_toman_int(ejare, default=0) if ejare is not None else None

        if price < 0:
            raise ValueError("Price cannot be negative")
        if bedrooms < 0 or bedrooms > 50:
            raise ValueError("Bedrooms must be between 0 and 50")
        if bathrooms < 0 or bathrooms > 50:
            raise ValueError("Bathrooms must be between 0 and 50")
        if square_feet < 0 or square_feet > 10000000:
            raise ValueError("Square feet must be between 0 and 10,000,000")
        if year_built and (year_built < 1800 or year_built > 2030):
            raise ValueError("Year built must be between 1800 and 2030")
        if parking_spaces < 0 or parking_spaces > 100:
            raise ValueError("Parking spaces must be between 0 and 100")
        if floors < 1 or floors > 200:
            raise ValueError("Floors must be between 1 and 200")
        if units < 1 or units > 10000:
            raise ValueError("Units must be between 1 and 10,000")
        
        # Validate agent exists if provided
        if agent_id:
            agent = db.session.get(Agent, agent_id)
            if not agent:
                raise ValueError(f"Agent with ID {agent_id} not found")
        
        # Validate listing type specific fields
        if listing_type == "rental":
            if not rahn and not ejare:
                raise ValueError("Either Rahn or Ejare is required for rental properties")
            if rahn and rahn < 0:
                raise ValueError("Rahn amount cannot be negative")
            if ejare and ejare <= 0:
                raise ValueError("Ejare amount must be greater than zero")
        elif listing_type == "sale":
            if price <= 0:
                raise ValueError("Sale price must be greater than zero")
        
        # Create property object
        property_obj = Property()
        property_obj.title = title.strip()
        property_obj.address = address.strip()
        property_obj.price = price
        property_obj.property_type = property_type.strip().lower()
        property_obj.bedrooms = bedrooms
        property_obj.bathrooms = bathrooms
        property_obj.square_feet = square_feet
        property_obj.description = description.strip() if description else ""
        property_obj.status = status
        property_obj.agent_id = agent_id
        property_obj.year_built = year_built
        property_obj.parking_spaces = parking_spaces
        property_obj.floors = floors
        property_obj.units = units
        property_obj.property_condition = property_condition
        property_obj.heating_type = heating_type.strip() if heating_type else ""
        property_obj.cooling_type = cooling_type.strip() if cooling_type else ""
        property_obj.rental_price = rental_price
        property_obj.neighborhood = neighborhood.strip() if neighborhood else ""
        property_obj.property_category = property_category
        property_obj.listing_type = listing_type
        property_obj.rahn = rahn
        property_obj.ejare = ejare
        property_obj.property_features = property_features.strip() if property_features else ""
        property_obj.latitude = latitude
        property_obj.longitude = longitude
        property_obj.image_filename = image_filename
        
        # Set additional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(property_obj, key):
                setattr(property_obj, key, value)
        
        db.session.add(property_obj)
        db.session.flush()  # Get the ID without committing

        self.logger.info(f"Created property {property_obj.id}: {title} at {address}")
        self._invalidate_property_caches(property_obj.id)
        
        # Check for AI extraction flag and save history if present
        is_ai_extracted = kwargs.get('is_ai_extracted')
        ai_raw_data = kwargs.get('ai_raw_data')

        if str(is_ai_extracted).lower() == 'true' and ai_raw_data:
            property_obj.source = "autofill"
            try:
                self.add_ai_history(property_obj.id, ai_raw_data, user_note="Initial AI Extraction")
            except Exception as e:
                self.logger.error(f"Failed to save initial AI history for property {property_obj.id}: {e}")

        # Log property creation to activity log
        try:
            activity_log = PropertyActivityLog(
                property_id=property_obj.id,
                action='created',
                description=f"Property '{property_obj.title}' created",
                new_value=str({
                    'title': property_obj.title,
                    'address': property_obj.address,
                    'price': property_obj.price,
                    'property_type': property_obj.property_type,
                    'listing_type': property_obj.listing_type,
                    'status': property_obj.status
                }),
                change_source='manual',
                changed_by=kwargs.get('changed_by', 'system')
            )
            db.session.add(activity_log)
            db.session.flush()
        except Exception as e:
            self.logger.error(f"Failed to log property creation activity for property {property_obj.id}: {e}")

        return property_obj
    
    @with_transaction()
    @log_execution
    def update_property_with_validation(self, property_id: int, **kwargs) -> Optional[Property]:
        """Update a property with comprehensive validation and transaction management"""
        
        property_obj = db.session.get(Property, property_id)
        if not property_obj:
            raise ValueError(f"Property with ID {property_id} not found")
        if self._is_deleted(property_obj):
            raise ValueError(f"Property with ID {property_id} is deleted")
        
        # Store original values for logging
        original_values = {}
        changes_made = []
        
        # Validate and apply updates
        for key, value in kwargs.items():
            if not hasattr(property_obj, key):
                continue
                
            original_value = getattr(property_obj, key)
            original_values[key] = original_value

            if key in {"price", "rental_price", "rahn", "ejare", "price_per_meter"}:
                value = self._to_toman_int(value) if value is not None else None
            
            # Skip if no change
            if original_value == value:
                continue
            
            # Validate specific fields
            if key == "title" and (not value or not str(value).strip()):
                raise ValueError("Property title cannot be empty")
            elif key == "address" and (not value or not str(value).strip()):
                raise ValueError("Property address cannot be empty")
            elif key == "price" and value < 0:
                raise ValueError("Price cannot be negative")
            elif key == "bedrooms" and (value < 0 or value > 50):
                raise ValueError("Bedrooms must be between 0 and 50")
            elif key == "bathrooms" and (value < 0 or value > 50):
                raise ValueError("Bathrooms must be between 0 and 50")
            elif key == "square_feet" and (value < 0 or value > 10000000):
                raise ValueError("Square feet must be between 0 and 10,000,000")
            elif key == "year_built" and value and (value < 1800 or value > 2030):
                raise ValueError("Year built must be between 1800 and 2030")
            elif key == "agent_id" and value:
                agent = db.session.get(Agent, value)
                if not agent:
                    raise ValueError(f"Agent with ID {value} not found")
            
            # Apply the change
            setattr(property_obj, key, value)
            changes_made.append(f"{key}: {original_value} -> {value}")
        
        if changes_made:
            property_obj.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.logger.info(f"Updated property {property_id}: {', '.join(changes_made)}")
            self._invalidate_property_caches(property_id)

            # Log property update to activity log
            try:
                # Determine specific action based on what changed
                price_changed = any('price:' in change for change in changes_made)
                status_changed = any('status:' in change for change in changes_made)

                if price_changed:
                    action = 'price_changed'
                    description = f"Price changed for property '{property_obj.title}'"
                elif status_changed:
                    action = 'status_changed'
                    description = f"Status changed for property '{property_obj.title}'"
                else:
                    action = 'updated'
                    description = f"Property '{property_obj.title}' updated"

                # Get old and new values for specific fields if they changed
                old_values_dict = {}
                new_values_dict = {}

                for key, value in kwargs.items():
                    if hasattr(property_obj, key) and key in original_values:
                        old_values_dict[key] = original_values[key]
                        new_values_dict[key] = getattr(property_obj, key)

                activity_log = PropertyActivityLog(
                    property_id=property_obj.id,
                    action=action,
                    description=description,
                    old_value=str(old_values_dict) if old_values_dict else None,
                    new_value=str(new_values_dict) if new_values_dict else None,
                    change_source='manual',
                    changed_by=kwargs.get('changed_by', 'system')
                )
                db.session.add(activity_log)
                db.session.flush()
            except Exception as e:
                self.logger.error(f"Failed to log property update activity for property {property_id}: {e}")

        return property_obj
    
    @with_transaction()
    @log_execution
    def delete_property_with_validation(self, property_id: int, force: bool = False) -> bool:
        """Delete a property with validation and transaction management"""
        
        property_obj = db.session.get(Property, property_id)
        if not property_obj:
            raise ValueError(f"Property with ID {property_id} not found")
        if self._is_deleted(property_obj):
            return True
        
        # Check for active deals unless forced
        if not force and hasattr(property_obj, 'deals') and property_obj.deals:
            active_deals = [
                d
                for d in property_obj.deals
                if getattr(d, "is_deleted", False) is not True
                and getattr(d, "status", None) not in ["closed_won", "closed_lost"]
            ]
            if active_deals:
                raise ValueError(f"Cannot delete property - it has {len(active_deals)} active deal(s)")
        
        property_title = property_obj.title
        if self._supports_soft_delete(property_obj):
            property_obj.is_deleted = True
            property_obj.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
            property_obj.status = "archived"
        else:
            # Legacy fallback used by non-mapped test doubles.
            db.session.delete(property_obj)
        self._invalidate_property_caches(property_id)

        # Log property deletion to activity log
        try:
            activity_log = PropertyActivityLog(
                property_id=property_obj.id,
                action='deleted',
                description=f"Property '{property_title}' deleted",
                old_value=str({
                    'title': property_obj.title,
                    'address': property_obj.address,
                    'price': property_obj.price,
                    'property_type': property_obj.property_type,
                    'listing_type': property_obj.listing_type,
                    'status': property_obj.status
                }) if hasattr(property_obj, 'title') else None,
                change_source='manual',
                changed_by='system'  # Since delete method doesn't have changed_by parameter
            )
            db.session.add(activity_log)
            db.session.flush()
        except Exception as e:
            self.logger.error(f"Failed to log property deletion activity for property {property_id}: {e}")

        self.logger.info(f"Deleted property {property_id}: {property_title}")
        return True
    
    @log_execution
    def get_property_statistics(self, property_id: int) -> Dict:
        """Get comprehensive statistics for a property"""
        try:
            property_obj = self.get_property_with_validation(property_id)
            if not property_obj:
                return {}
            
            stats = {
                'property_id': property_id,
                'total_deals': 0,
                'active_deals': 0,
                'closed_deals': 0,
                'won_deals': 0,
                'lost_deals': 0,
                'total_deal_value': 0,
                'average_deal_value': 0,
                'days_on_market': 0,
                'last_activity': None,
                'view_count': 0,  # Placeholder for future implementation
                'inquiry_count': 0,  # Placeholder for future implementation
            }
            
            # Calculate days on market
            if property_obj.created_at:
                days_on_market = (datetime.now(timezone.utc).replace(tzinfo=None) - property_obj.created_at).days
                stats['days_on_market'] = days_on_market
            
            # Calculate deal statistics
            if hasattr(property_obj, 'deals') and property_obj.deals:
                deals = [d for d in property_obj.deals if getattr(d, "is_deleted", False) is not True]
                stats['total_deals'] = len(deals)
                
                active_deals = [d for d in deals if d.status not in ["closed_won", "closed_lost"]]
                closed_deals = [d for d in deals if d.status in ["closed_won", "closed_lost"]]
                won_deals = [d for d in deals if d.status == "closed_won"]
                lost_deals = [d for d in deals if d.status == "closed_lost"]
                
                stats['active_deals'] = len(active_deals)
                stats['closed_deals'] = len(closed_deals)
                stats['won_deals'] = len(won_deals)
                stats['lost_deals'] = len(lost_deals)
                
                # Calculate deal values (support legacy `value` attr in tests/mocks).
                deal_values = []
                for deal in deals:
                    amount = getattr(deal, "offer_amount", None)
                    if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount == 0:
                        amount = getattr(deal, "value", None)
                    if isinstance(amount, (int, float)) and not isinstance(amount, bool):
                        deal_values.append(amount)
                if deal_values:
                    stats['total_deal_value'] = sum(deal_values)
                    stats['average_deal_value'] = stats['total_deal_value'] / len(deal_values)
                
                # Find last activity
                if deals:
                    last_activity = max(
                        (d.updated_at or d.created_at for d in deals if d.updated_at or d.created_at),
                        default=None
                    )
                    stats['last_activity'] = last_activity
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculating property statistics for {property_id}: {str(e)}")
            return {}
    
    @log_execution
    def search_properties_advanced(
        self,
        search_query: str = "",
        filters: Optional[Dict] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 10,
        include_inactive: bool = False
    ) -> Dict:
        """Advanced property search with filtering, sorting, and pagination"""
        try:
            filters = filters or {}
            
            # Start with base query
            query = Property.query.options(selectinload(Property.agent)).filter(
                Property.is_deleted.is_(False)
            )
            
            # Apply status filter
            if not include_inactive:
                query = query.filter(Property.status == 'active')
            
            # Apply search query
            if search_query:
                search_term = f"%{search_query}%"
                query = query.filter(
                    or_(
                        Property.title.ilike(search_term),
                        Property.address.ilike(search_term),
                        Property.description.ilike(search_term),
                        Property.neighborhood.ilike(search_term)
                    )
                )
            
            # Apply filters
            for key, value in filters.items():
                if not value:
                    continue
                    
                if key == "property_type":
                    query = query.filter(Property.property_type == value)
                elif key == "property_category":
                    query = query.filter(Property.property_category == value)
                elif key == "property_condition":
                    query = query.filter(Property.property_condition == value)
                elif key == "neighborhood":
                    query = query.filter(Property.neighborhood == value)
                elif key == "listing_type":
                    query = query.filter(Property.listing_type == value)
                elif key == "agent_id":
                    query = query.filter(Property.agent_id == value)
                elif key == "min_price":
                    query = query.filter(Property.price >= value)
                elif key == "max_price":
                    query = query.filter(Property.price <= value)
                elif key == "min_bedrooms":
                    query = query.filter(Property.bedrooms >= value)
                elif key == "max_bedrooms":
                    query = query.filter(Property.bedrooms <= value)
                elif key == "min_bathrooms":
                    query = query.filter(Property.bathrooms >= value)
                elif key == "max_bathrooms":
                    query = query.filter(Property.bathrooms <= value)
                elif key == "min_sqft":
                    query = query.filter(Property.square_feet >= value)
                elif key == "max_sqft":
                    query = query.filter(Property.square_feet <= value)
                elif key == "year_built_min":
                    query = query.filter(Property.year_built >= value)
                elif key == "year_built_max":
                    query = query.filter(Property.year_built <= value)
            
            # Apply sorting
            sort_column = getattr(Property, sort_by, Property.created_at)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
            
            # Apply pagination
            pagination = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # Add agent names to properties
            for prop in pagination.items:
                setattr(prop, "agent_name", prop.agent.name if prop.agent else "Unassigned")
            
            return {
                'properties': pagination.items,
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'next_page': pagination.next_num if pagination.has_next else None,
                'prev_page': pagination.prev_num if pagination.has_prev else None
            }
            
        except Exception as e:
            self.logger.error(f"Error in advanced property search: {str(e)}")
            return {
                'properties': [],
                'total': 0,
                'pages': 0,
                'current_page': page,
                'per_page': per_page,
                'has_next': False,
                'has_prev': False,
                'next_page': None,
                'prev_page': None,
                'error': str(e)
            }
    
    @log_execution
    def bulk_update_properties(self, property_ids: List[int], updates: Dict) -> Dict:
        """Bulk update multiple properties with transaction management"""
        results = {
            'updated': [],
            'failed': [],
            'total_requested': len(property_ids),
            'total_updated': 0,
            'total_failed': 0
        }
        
        try:
            with database_transaction():
                for property_id in property_ids:
                    try:
                        updated_property = self.update_property_with_validation(property_id, **updates)
                        if updated_property:
                            results['updated'].append({
                                'id': property_id,
                                'title': updated_property.title
                            })
                            results['total_updated'] += 1
                        else:
                            results['failed'].append({
                                'id': property_id,
                                'error': 'Property not found'
                            })
                            results['total_failed'] += 1
                    except Exception as e:
                        results['failed'].append({
                            'id': property_id,
                            'error': str(e)
                        })
                        results['total_failed'] += 1
                
                self.logger.info(f"Bulk update completed: {results['total_updated']} updated, {results['total_failed']} failed")
                
        except Exception as e:
            self.logger.error(f"Bulk update transaction failed: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    @log_execution
    def get_property_history(self, property_id: int) -> List[Dict]:
        """Get property change history from audit log"""
        try:
            # Verify property exists
            property_obj = self.get_property(property_id)
            if not property_obj:
                return []

            # Query the PropertyActivityLog for this property
            activity_logs = PropertyActivityLog.query.filter_by(
                property_id=property_id
            ).order_by(desc(PropertyActivityLog.created_at)).all()

            # Convert to dict format for compatibility
            history = []
            for log in activity_logs:
                history.append({
                    'id': log.id,
                    'action': log.action,
                    'description': log.description,
                    'timestamp': log.created_at,
                    'old_value': log.old_value,
                    'new_value': log.new_value,
                    'change_source': log.change_source,
                    'changed_by': log.changed_by,
                    'sync_version': log.sync_version
                })

            return history
        except Exception as e:
            self.logger.error(f"Error fetching property history for {property_id}: {str(e)}")
            return []

    @log_execution
    def add_ai_history(self, property_id: int, raw_data: str, user_note: Optional[str] = None) -> Optional[PropertyAIHistory]:
        """Add a new AI extraction history record"""
        try:
            history = PropertyAIHistory(
                property_id=property_id,
                raw_data=raw_data,
                user_note=user_note
            )
            db.session.add(history)
            db.session.commit()
            return history
        except Exception as e:
            self.logger.error(f"Error adding AI history for property {property_id}: {str(e)}")
            db.session.rollback()
            return None

    @log_execution
    def get_ai_history(self, property_id: int) -> List[PropertyAIHistory]:
        """Get AI extraction history for a property"""
        try:
            return PropertyAIHistory.query.filter_by(property_id=property_id).order_by(desc(PropertyAIHistory.created_at)).all()
        except Exception as e:
            self.logger.error(f"Error fetching AI history for property {property_id}: {str(e)}")
            return []

    @log_execution
    def delete_ai_history(self, history_id: int) -> bool:
        """Delete an AI extraction history record"""
        try:
            history = db.session.get(PropertyAIHistory, history_id)
            if history:
                db.session.delete(history)
                db.session.commit()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error deleting AI history {history_id}: {str(e)}")
            return False

    @log_execution
    def update_deal(self, deal_id: int, **kwargs) -> Optional[Deal]:
        """Update a deal"""
        deal = db.session.get(Deal, deal_id)
        if deal and not deal.is_deleted:
            old_status = deal.status
            for key, value in kwargs.items():
                if hasattr(deal, key):
                    if key == "offer_amount" and value is not None:
                        value = self._to_toman_int(value)
                    setattr(deal, key, value)
            deal.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.session.commit()
            self._invalidate_market_cache()

            # Trigger workflow automation for stage changes.
            try:
                if "status" in kwargs and kwargs.get("status") != old_status:
                    from services.automation_service import automation_service

                    automation_service.handle_deal_stage_changed(
                        deal,
                        old_status=old_status,
                        new_status=kwargs.get("status"),
                    )
            except Exception as e:
                self.logger.warning(f"Deal stage automation failed for deal {deal_id}: {e}")
        return deal if deal and not deal.is_deleted else None

    # Agent operations
    @log_execution
    def add_agent(
        self, name: str, email: str, phone: str, specialization: str = "", bio: str = ""
    ) -> Agent:
        """Add a new agent"""
        agent = Agent()
        agent.name = name
        agent.email = email
        agent.phone = phone
        agent.specialization = specialization
        agent.bio = bio
        db.session.add(agent)
        db.session.commit()
        self._invalidate_market_cache()
        return agent

    @log_execution
    def get_agents(self) -> List[Agent]:
        """Get all agents"""
        return Agent.query.filter(Agent.is_deleted.is_(False)).order_by(Agent.name).all()

    @log_execution
    def get_agent(self, agent_id: int) -> Optional[Agent]:
        """Get an agent by ID"""
        agent = db.session.get(Agent, agent_id)
        if agent and agent.is_deleted:
            return None
        return agent

    @with_transaction()
    @log_execution
    def update_agent(self, agent_id: int, **kwargs) -> Optional[Agent]:
        """Update an agent with transaction management"""
        agent = db.session.get(Agent, agent_id)
        if not agent or agent.is_deleted:
            return None
        
        # Store original values for potential rollback logging
        original_values = {}
        for key, value in kwargs.items():
            if value is None:
                continue
            if hasattr(agent, key):
                original_values[key] = getattr(agent, key)
                setattr(agent, key, value)
        
        self.logger.info(f"Updated agent {agent_id}: {kwargs}")
        self._invalidate_market_cache()
        return agent

    @with_transaction()
    @log_execution
    def delete_agent(self, agent_id: int) -> bool:
        """Delete an agent with transaction management"""
        agent = db.session.get(Agent, agent_id)
        if not agent:
            return False
        if agent.is_deleted:
            return True
        
        # Check for dependencies before deletion
        active_properties = db.session.query(Property).filter_by(
            agent_id=agent_id,
            status='active',
            is_deleted=False,
        ).count()
        active_deals = (
            db.session.query(Deal)
            .filter_by(agent_id=agent_id, is_deleted=False)
            .filter(Deal.status.notin_(['closed_won', 'closed_lost']))
            .count()
        )
        
        if active_properties > 0:
            raise ValueError(f"Cannot delete agent - they have {active_properties} active listing(s)")
        if active_deals > 0:
            raise ValueError(f"Cannot delete agent - they have {active_deals} active deal(s)")
        
        agent_name = agent.name
        agent.is_deleted = True
        agent.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self._invalidate_market_cache()
        self.logger.info(f"Deleted agent: {agent_name} (ID: {agent_id})")
        return True

    # Customer operations
    @log_execution
    def add_customer(
        self,
        name: str,
        email: str,
        phone: str,
        budget_min: int = 0,
        budget_max: int = 0,
        preferred_bedrooms: int = 0,
        preferred_bathrooms: int = 0,
        preferred_type: str = "",
        location_preference: str = "",
    ) -> Customer:
        """Add a new customer"""
        customer = Customer()
        customer.name = name
        customer.email = email
        customer.phone = phone
        customer.budget_min = self._to_toman_int(budget_min)
        customer.budget_max = self._to_toman_int(budget_max)
        customer.preferred_bedrooms = preferred_bedrooms
        customer.preferred_bathrooms = preferred_bathrooms
        customer.preferred_type = preferred_type
        customer.location_preference = location_preference
        db.session.add(customer)
        db.session.commit()
        self._invalidate_customer_caches(customer.id)
        return customer

    @log_execution
    def get_customers(self) -> List[Customer]:
        """Get all customers"""
        return self.customer_repository.list_all()

    @log_execution
    def get_customer(self, customer_id: int) -> Optional[Customer]:
        """Get a customer by ID"""
        return self.customer_repository.get_by_id(customer_id)

    @with_transaction()
    @log_execution
    def update_customer(self, customer_id: int, **kwargs) -> Optional[Customer]:
        """Update a customer with transaction management"""
        customer = db.session.get(Customer, customer_id)
        if not customer or customer.is_deleted:
            return None
        
        # Validate budget ranges if provided
        if 'budget_min' in kwargs and 'budget_max' in kwargs:
            budget_min = kwargs.get('budget_min', customer.budget_min)
            budget_max = kwargs.get('budget_max', customer.budget_max)
            if budget_min is None:
                budget_min = customer.budget_min
            if budget_max is None:
                budget_max = customer.budget_max
            if budget_min > 0 and budget_max > 0 and budget_min > budget_max:
                raise ValueError("Minimum budget cannot be greater than maximum budget")
        
        # Store original values for logging
        original_values = {}
        for key, value in kwargs.items():
            if value is None:
                continue
            if hasattr(customer, key):
                if key in {"budget_min", "budget_max"}:
                    value = self._to_toman_int(value)
                original_values[key] = getattr(customer, key)
                setattr(customer, key, value)

        db.session.commit()
        self.logger.info(f"Updated customer {customer_id}: {kwargs}")
        self._invalidate_customer_caches(customer_id)
        return customer

    @with_transaction()
    @log_execution
    def delete_customer(self, customer_id: int) -> bool:
        """Delete a customer with transaction management"""
        customer = db.session.get(Customer, customer_id)
        if not customer:
            return False
        if self._is_deleted(customer):
            return True

        customer_name = customer.name
        if self._supports_soft_delete(customer):
            customer.is_deleted = True
            customer.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)

            # Preserve non-destructive semantics while keeping legacy cascade behavior:
            # deleting a customer should hide their deals from default reads.
            related_deals = (
                Deal.query.filter(
                    Deal.customer_id == customer_id,
                    Deal.is_deleted.is_(False),
                ).all()
            )
            for deal in related_deals:
                deal.is_deleted = True
                deal.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            db.session.delete(customer)

        self._invalidate_customer_caches(customer_id)
        self.logger.info(f"Deleted customer: {customer_name} (ID: {customer_id})")
        return True

    # Deal operations
    @log_execution
    def add_deal(
        self,
        property_id: int,
        customer_id: int,
        agent_id: Optional[int] = None,
        status: str = "prospecting",
        offer_amount: int = 0,
    ) -> Deal:
        """Add a new deal"""
        deal = Deal()
        deal.property_id = property_id
        deal.customer_id = customer_id
        if agent_id is None:
            linked_property = self.get_property(property_id)
            agent_id = linked_property.agent_id if linked_property else None
        deal.agent_id = agent_id
        deal.status = status
        deal.offer_amount = self._to_toman_int(offer_amount)
        db.session.add(deal)
        db.session.commit()
        self._invalidate_market_cache()
        return deal

    @log_execution
    def get_deals(self) -> List[Deal]:
        """Get all deals with relations for pipeline/list rendering."""
        from sqlalchemy.orm import joinedload

        return (
            Deal.query.filter(Deal.is_deleted.is_(False))
            .options(
                joinedload(Deal.property),
                joinedload(Deal.customer),
                joinedload(Deal.agent),
            )
            .order_by(desc(Deal.created_at))
            .all()
        )

    @log_execution
    def get_deal(self, deal_id: int) -> Optional[Deal]:
        """Get a deal by ID"""
        deal = db.session.get(Deal, deal_id)
        if deal and deal.is_deleted:
            return None
        return deal

    @log_execution
    def get_deal_with_relations(self, deal_id: int) -> Optional[Deal]:
        """Get a deal by ID with all related entities loaded"""
        from sqlalchemy.orm import joinedload
        return (
            Deal.query
            .options(
                joinedload(Deal.property),
                joinedload(Deal.customer),
                joinedload(Deal.agent)
            )
            .filter(Deal.id == deal_id, Deal.is_deleted.is_(False))
            .first()
        )

    @with_transaction()
    @log_execution
    def delete_deal(self, deal_id: int) -> bool:
        """Delete a deal with transaction management"""
        deal = db.session.get(Deal, deal_id)
        if not deal:
            return False
        if deal.is_deleted:
            return True
        
        # Log deal information before deletion
        deal_info = f"Deal for property '{deal.property.title if deal.property else 'Unknown'}' with customer '{deal.customer.name if deal.customer else 'Unknown'}'"
        
        deal.is_deleted = True
        deal.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self._invalidate_market_cache()
        self.logger.info(f"Deleted deal: {deal_info} (ID: {deal_id})")
        return True

    # Task operations
    @log_execution
    def add_task(
        self,
        title: str,
        description: str,
        agent_id: int,
        priority: str = "medium",
        status: str = "pending",
        due_date: Optional[datetime] = None,
    ) -> Task:
        """Add a new task"""
        task = Task()
        task.title = title
        task.description = description
        task.agent_id = agent_id
        task.priority = priority
        task.status = status
        task.due_date = due_date
        db.session.add(task)
        db.session.commit()
        return task

    @log_execution
    def get_tasks(self, agent_id: Optional[int] = None, status: Optional[str] = None) -> List[Task]:
        """Get tasks with optional filtering (eager-load agent for list/dashboard)."""
        from sqlalchemy.orm import selectinload

        query = Task.query.options(selectinload(Task.agent)).filter(
            Task.is_deleted.is_(False)
        )

        if agent_id:
            query = query.filter(Task.agent_id == agent_id)
        if status:
            query = query.filter(Task.status == status)

        return query.order_by(desc(Task.created_at)).all()

    @log_execution
    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a task by ID"""
        task = db.session.get(Task, task_id)
        if task and task.is_deleted:
            return None
        return task

    @with_transaction()
    @log_execution
    def update_task(self, task_id: int, **kwargs) -> Optional[Task]:
        """Update a task with transaction management"""
        task = db.session.get(Task, task_id)
        if not task or task.is_deleted:
            return None
        previous_status = task.status
        
        # Validate due date if provided
        if 'due_date' in kwargs and kwargs['due_date']:
            due_date = kwargs['due_date']
            if hasattr(due_date, 'date'):
                due_date = due_date.date()
            if due_date < datetime.now().date():
                raise ValueError("Due date cannot be in the past")
        
        # Validate status transitions
        if 'status' in kwargs:
            valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
            if kwargs['status'] not in valid_statuses:
                raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        # Store original values for logging
        original_values = {}
        for key, value in kwargs.items():
            if value is None:
                continue
            if hasattr(task, key):
                original_values[key] = getattr(task, key)
                setattr(task, key, value)
        
        # Set completion timestamp if status changed to completed
        if kwargs.get('status') == 'completed' and previous_status != 'completed':
            task.completed_at = datetime.now()
        
        self.logger.info(f"Updated task {task_id}: {kwargs}")
        return task

    @with_transaction()
    @log_execution
    def delete_task(self, task_id: int) -> bool:
        """Delete a task with transaction management"""
        task = db.session.get(Task, task_id)
        if not task:
            return False
        if task.is_deleted:
            return True
        
        task_title = task.title
        task.is_deleted = True
        task.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.logger.info(f"Deleted task: {task_title} (ID: {task_id})")
        return True

    @log_execution
    def complete_task(self, task_id: int) -> Optional[Task]:
        """Mark a task as completed"""
        task = db.session.get(Task, task_id)
        if task and not task.is_deleted:
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.session.commit()
        return task

    # Export operations
    @log_execution
    def export_recommendations_data(self, customer_id: Optional[int] = None) -> Dict:
        """Export recommendations data for reporting"""
        from sqlalchemy.orm import joinedload
        
        # Get properties with their agents
        properties_query = Property.query.options(joinedload(Property.agent)).filter(
            Property.is_deleted.is_(False)
        )
        
        if customer_id:
            # If customer_id provided, filter properties based on customer preferences
            customer = self.get_customer(customer_id)
            if customer:
                properties_query = properties_query.filter(
                    Property.price >= customer.budget_min,
                    Property.price <= customer.budget_max if customer.budget_max > 0 else True,
                    Property.bedrooms >= customer.preferred_bedrooms if customer.preferred_bedrooms > 0 else True,
                    Property.bathrooms >= customer.preferred_bathrooms if customer.preferred_bathrooms > 0 else True,
                    Property.property_type == customer.preferred_type if customer.preferred_type else True
                )
        
        properties = properties_query.filter(Property.status == "active").all()
        
        # Format data for export
        export_data = {
            "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "customer_id": customer_id,
            "total_properties": len(properties),
            "properties": []
        }
        
        for prop in properties:
            prop_data = prop.to_dict()
            if prop.agent:
                prop_data["agent_name"] = prop.agent.name
                prop_data["agent_email"] = prop.agent.email
                prop_data["agent_phone"] = prop.agent.phone
            else:
                prop_data["agent_name"] = "N/A"
                prop_data["agent_email"] = None
                prop_data["agent_phone"] = None
            export_data["properties"].append(prop_data)
        
        return export_data

    @log_execution
    def export_deals_report(self) -> Dict:
        """Export deals data for reporting"""
        from sqlalchemy.orm import joinedload
        
        # Get all deals with related entities
        deals = (
            Deal.query
            .options(
                joinedload(Deal.property),
                joinedload(Deal.customer),
                joinedload(Deal.agent)
            )
            .filter(Deal.is_deleted.is_(False))
            .order_by(desc(Deal.created_at))
            .all()
        )
        
        # Calculate summary statistics
        total_deals = len(deals)
        total_value = sum(deal.offer_amount for deal in deals)
        active_deals = [deal for deal in deals if deal.status in ["prospecting", "qualified", "proposal", "negotiation"]]
        closed_deals = [deal for deal in deals if deal.status == "closed"]
        
        # Format data for export
        export_data = {
            "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "summary": {
                "total_deals": total_deals,
                "total_value": total_value,
                "active_deals": len(active_deals),
                "closed_deals": len(closed_deals),
                "average_deal_value": total_value / total_deals if total_deals > 0 else 0
            },
            "deals": []
        }
        
        for deal in deals:
            deal_data = deal.to_dict()
            if deal.property:
                deal_data["property_title"] = deal.property.title
                deal_data["property_address"] = deal.property.address
                deal_data["property_price"] = deal.property.price
            else:
                deal_data["property_title"] = "N/A"
                deal_data["property_address"] = None
                deal_data["property_price"] = None
            if deal.customer:
                deal_data["customer_name"] = deal.customer.name
                deal_data["customer_email"] = deal.customer.email
                deal_data["customer_phone"] = deal.customer.phone
            else:
                deal_data["customer_name"] = "N/A"
                deal_data["customer_email"] = None
                deal_data["customer_phone"] = None
            if deal.agent:
                deal_data["agent_name"] = deal.agent.name
                deal_data["agent_email"] = deal.agent.email
            else:
                deal_data["agent_name"] = "N/A"
                deal_data["agent_email"] = None
            export_data["deals"].append(deal_data)
        
        return export_data

    # Dashboard statistics
    @log_execution
    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        return self.dashboard_statistics_repository.get_dashboard_stats()

    # Analysis operations



# Global database service instance
database_service = DatabaseService()
