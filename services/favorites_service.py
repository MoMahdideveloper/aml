"""
Favorites Service for managing property favorites functionality
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from database import db
from sqlalchemy_models import Property, PropertyFavorite
from database_transaction_manager import with_transaction, safe_database_operation, database_transaction
from utils.execution_tracer import log_execution


class FavoritesService:
    """Service class to handle property favorites operations"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @with_transaction()
    @log_execution
    def add_favorite(
        self,
        property_id: int,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None
    ) -> PropertyFavorite:
        """
        Add a property to favorites
        
        Args:
            property_id: ID of the property to favorite
            user_id: ID of the user (optional for future user system)
            category: Optional category for the favorite
            notes: Optional notes about the favorite
            
        Returns:
            PropertyFavorite: The created favorite object
            
        Raises:
            ValueError: If property doesn't exist or favorite already exists
            IntegrityError: If database constraints are violated
        """
        # Validate property exists
        property_obj = db.session.get(Property, property_id)
        if not property_obj:
            raise ValueError(f"Property with ID {property_id} not found")
        
        # Check if favorite already exists for this user/property combination
        existing_favorite = PropertyFavorite.query.filter_by(
            property_id=property_id,
            user_id=user_id
        ).first()
        
        if existing_favorite:
            raise ValueError(f"Property {property_id} is already favorited by user {user_id}")
        
        # Validate category if provided
        valid_categories = ["potential_buy", "investment", "watch_list", "dream_home", "comparison"]
        if category and category not in valid_categories:
            self.logger.warning(f"Unknown category '{category}' used for favorite")
        
        # Create favorite
        favorite = PropertyFavorite(
            property_id=property_id,
            user_id=user_id,
            category=category,
            notes=notes.strip() if notes else None
        )
        
        db.session.add(favorite)
        db.session.flush()  # Get the ID without committing
        
        self.logger.info(f"Added property {property_id} to favorites for user {user_id}")
        return favorite

    @with_transaction()
    @log_execution
    def remove_favorite(
        self,
        property_id: Optional[int] = None,
        user_id: Optional[int] = None,
        favorite_id: Optional[int] = None
    ) -> bool:
        """
        Remove a property from favorites
        
        Args:
            property_id: ID of the property to unfavorite
            user_id: ID of the user (optional for future user system)
            favorite_id: Direct favorite ID (alternative to property_id/user_id)
            
        Returns:
            bool: True if favorite was removed, False if not found
            
        Raises:
            ValueError: If neither favorite_id nor property_id is provided
        """
        if favorite_id:
            # Remove by favorite ID
            favorite = db.session.get(PropertyFavorite, favorite_id)
            if not favorite:
                return False
        else:
            # Remove by property_id and user_id
            if not property_id:
                raise ValueError("Either favorite_id or property_id must be provided")
            
            favorite = PropertyFavorite.query.filter_by(
                property_id=property_id,
                user_id=user_id
            ).first()
            
            if not favorite:
                return False
        
        property_title = favorite.property.title if favorite.property else "Unknown"
        db.session.delete(favorite)
        
        self.logger.info(f"Removed favorite for property '{property_title}' (ID: {favorite.property_id}) for user {favorite.user_id}")
        return True

    @log_execution
    def get_user_favorites(
        self,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
        include_property_details: bool = True,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: Optional[int] = None
    ) -> List[PropertyFavorite]:
        """
        Get favorites for a user with optional filtering and sorting
        
        Args:
            user_id: ID of the user (None for all favorites)
            category: Filter by category
            include_property_details: Whether to load property details
            sort_by: Field to sort by (created_at, updated_at, property_title)
            sort_order: Sort order (asc, desc)
            limit: Maximum number of results
            
        Returns:
            List[PropertyFavorite]: List of favorite objects
        """
        try:
            query = PropertyFavorite.query
            
            # Filter by user_id
            if user_id is not None:
                query = query.filter(PropertyFavorite.user_id == user_id)
            
            # Filter by category
            if category:
                query = query.filter(PropertyFavorite.category == category)
            
            # Include property details if requested
            if include_property_details:
                query = query.options(selectinload(PropertyFavorite.property))
            
            # Apply sorting
            if sort_by == "property_title" and include_property_details:
                # Join with Property table for title sorting
                query = query.join(Property)
                if sort_order.lower() == "desc":
                    query = query.order_by(desc(Property.title))
                else:
                    query = query.order_by(Property.title)
            else:
                # Sort by PropertyFavorite fields
                sort_column = getattr(PropertyFavorite, sort_by, PropertyFavorite.created_at)
                if sort_order.lower() == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(sort_column)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            favorites = query.all()
            
            self.logger.debug(f"Retrieved {len(favorites)} favorites for user {user_id}")
            return favorites
            
        except Exception as e:
            self.logger.error(f"Error retrieving favorites for user {user_id}: {str(e)}")
            return []

    @log_execution
    def is_favorited(
        self,
        property_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Check if a property is favorited by a user
        
        Args:
            property_id: ID of the property to check
            user_id: ID of the user (None checks if any favorites exist)
            
        Returns:
            bool: True if property is favorited, False otherwise
        """
        try:
            query = PropertyFavorite.query.filter(PropertyFavorite.property_id == property_id)
            
            if user_id is not None:
                query = query.filter(PropertyFavorite.user_id == user_id)
            
            return query.first() is not None
            
        except Exception as e:
            self.logger.error(f"Error checking if property {property_id} is favorited: {str(e)}")
            return False

    @log_execution
    def get_favorites_count(
        self,
        property_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> int:
        """
        Get count of favorites for a property or user
        
        Args:
            property_id: ID of the property (None for all properties)
            user_id: ID of the user (None for all users)
            
        Returns:
            int: Number of favorites
        """
        try:
            query = PropertyFavorite.query
            
            if property_id is not None:
                query = query.filter(PropertyFavorite.property_id == property_id)
            
            if user_id is not None:
                query = query.filter(PropertyFavorite.user_id == user_id)
            
            count = query.count()
            return count
            
        except Exception as e:
            self.logger.error(f"Error counting favorites: {str(e)}")
            return 0

    @log_execution
    def get_favorite_by_id(self, favorite_id: int) -> Optional[PropertyFavorite]:
        """
        Get a favorite by its ID
        
        Args:
            favorite_id: ID of the favorite
            
        Returns:
            PropertyFavorite: The favorite object or None if not found
        """
        try:
            return db.session.get(PropertyFavorite, favorite_id)
        except Exception as e:
            self.logger.error(f"Error fetching favorite {favorite_id}: {str(e)}")
            return None

    @with_transaction()
    @log_execution
    def update_favorite(
        self,
        favorite_id: int,
        category: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[PropertyFavorite]:
        """
        Update a favorite's category or notes
        
        Args:
            favorite_id: ID of the favorite to update
            category: New category (None to keep current)
            notes: New notes (None to keep current)
            
        Returns:
            PropertyFavorite: Updated favorite object or None if not found
            
        Raises:
            ValueError: If favorite not found
        """
        favorite = db.session.get(PropertyFavorite, favorite_id)
        if not favorite:
            raise ValueError(f"Favorite with ID {favorite_id} not found")
        
        changes_made = []
        
        if category is not None and category != favorite.category:
            # Validate category
            valid_categories = ["potential_buy", "investment", "watch_list", "dream_home", "comparison"]
            if category and category not in valid_categories:
                self.logger.warning(f"Unknown category '{category}' used for favorite")
            
            favorite.category = category
            changes_made.append(f"category: {favorite.category} -> {category}")
        
        if notes is not None and notes != favorite.notes:
            favorite.notes = notes.strip() if notes else None
            changes_made.append(f"notes updated")
        
        if changes_made:
            favorite.updated_at = datetime.utcnow()
            self.logger.info(f"Updated favorite {favorite_id}: {', '.join(changes_made)}")
        
        return favorite

    @log_execution
    def get_favorites_by_category(
        self,
        category: str,
        user_id: Optional[int] = None,
        include_property_details: bool = True
    ) -> List[PropertyFavorite]:
        """
        Get all favorites in a specific category
        
        Args:
            category: Category to filter by
            user_id: Optional user ID filter
            include_property_details: Whether to load property details
            
        Returns:
            List[PropertyFavorite]: List of favorites in the category
        """
        return self.get_user_favorites(
            user_id=user_id,
            category=category,
            include_property_details=include_property_details
        )

    @log_execution
    def get_popular_properties(
        self,
        limit: int = 10,
        min_favorites: int = 1
    ) -> List[Dict]:
        """
        Get most favorited properties
        
        Args:
            limit: Maximum number of properties to return
            min_favorites: Minimum number of favorites required
            
        Returns:
            List[Dict]: List of properties with favorite counts
        """
        try:
            # Query to get properties with favorite counts
            query = db.session.query(
                Property,
                func.count(PropertyFavorite.id).label('favorites_count')
            ).join(
                PropertyFavorite, Property.id == PropertyFavorite.property_id
            ).group_by(
                Property.id
            ).having(
                func.count(PropertyFavorite.id) >= min_favorites
            ).order_by(
                desc(func.count(PropertyFavorite.id))
            ).limit(limit)
            
            results = []
            for property_obj, count in query.all():
                results.append({
                    'property': property_obj,
                    'favorites_count': count
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting popular properties: {str(e)}")
            return []

    @with_transaction()
    @log_execution
    def bulk_remove_favorites(
        self,
        favorite_ids: List[int],
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Remove multiple favorites in a single transaction
        
        Args:
            favorite_ids: List of favorite IDs to remove
            user_id: Optional user ID for additional validation
            
        Returns:
            Dict: Results summary with removed/failed counts
        """
        results = {
            'removed': [],
            'failed': [],
            'total_requested': len(favorite_ids),
            'total_removed': 0,
            'total_failed': 0
        }
        
        try:
            for favorite_id in favorite_ids:
                try:
                    favorite = db.session.get(PropertyFavorite, favorite_id)
                    if not favorite:
                        results['failed'].append({
                            'id': favorite_id,
                            'error': 'Favorite not found'
                        })
                        results['total_failed'] += 1
                        continue
                    
                    # Additional user validation if provided
                    if user_id is not None and favorite.user_id != user_id:
                        results['failed'].append({
                            'id': favorite_id,
                            'error': 'User not authorized to remove this favorite'
                        })
                        results['total_failed'] += 1
                        continue
                    
                    property_title = favorite.property.title if favorite.property else "Unknown"
                    db.session.delete(favorite)
                    
                    results['removed'].append({
                        'id': favorite_id,
                        'property_title': property_title
                    })
                    results['total_removed'] += 1
                    
                except Exception as e:
                    results['failed'].append({
                        'id': favorite_id,
                        'error': str(e)
                    })
                    results['total_failed'] += 1
            
            self.logger.info(f"Bulk remove completed: {results['total_removed']} removed, {results['total_failed']} failed")
            
        except Exception as e:
            self.logger.error(f"Bulk remove transaction failed: {str(e)}")
            results['error'] = str(e)
        
        return results

    @log_execution
    def get_user_favorite_categories(self, user_id: Optional[int] = None) -> List[Dict]:
        """
        Get all categories used by a user with counts
        
        Args:
            user_id: ID of the user (None for all users)
            
        Returns:
            List[Dict]: List of categories with counts
        """
        try:
            query = db.session.query(
                PropertyFavorite.category,
                func.count(PropertyFavorite.id).label('count')
            ).filter(
                PropertyFavorite.category.isnot(None)
            )
            
            if user_id is not None:
                query = query.filter(PropertyFavorite.user_id == user_id)
            
            query = query.group_by(PropertyFavorite.category).order_by(desc(func.count(PropertyFavorite.id)))
            
            results = []
            for category, count in query.all():
                results.append({
                    'category': category,
                    'count': count
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting favorite categories: {str(e)}")
            return []

    @log_execution
    def get_favorites_statistics(self, user_id: Optional[int] = None) -> Dict:
        """
        Get comprehensive statistics about favorites
        
        Args:
            user_id: ID of the user (None for global statistics)
            
        Returns:
            Dict: Statistics about favorites
        """
        try:
            stats = {
                'total_favorites': 0,
                'categories': {},
                'most_recent': None,
                'oldest': None,
                'average_per_day': 0,
                'most_favorited_property': None
            }
            
            query = PropertyFavorite.query
            if user_id is not None:
                query = query.filter(PropertyFavorite.user_id == user_id)
            
            favorites = query.all()
            stats['total_favorites'] = len(favorites)
            
            if not favorites:
                return stats
            
            # Category breakdown
            for favorite in favorites:
                category = favorite.category or 'uncategorized'
                stats['categories'][category] = stats['categories'].get(category, 0) + 1
            
            # Date statistics
            dates = [f.created_at for f in favorites if f.created_at]
            if dates:
                stats['most_recent'] = max(dates)
                stats['oldest'] = min(dates)
                
                # Calculate average per day
                date_range = (max(dates) - min(dates)).days
                if date_range > 0:
                    stats['average_per_day'] = len(favorites) / date_range
            
            # Most favorited property (for global stats)
            if user_id is None:
                popular = self.get_popular_properties(limit=1)
                if popular:
                    stats['most_favorited_property'] = {
                        'property': popular[0]['property'],
                        'count': popular[0]['favorites_count']
                    }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting favorites statistics: {str(e)}")
            return {}