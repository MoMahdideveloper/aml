"""
Query building for property search.
"""

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from sqlalchemy_models import Property


def build_property_search_query(search_request):
    """
    Build a SQLAlchemy query for property search based on the search request DTO.

    Args:
        search_request: An instance of SearchRequest DTO

    Returns:
        SQLAlchemy query object for Property model
    """
    # Start with base query excluding deleted properties and eager loading agent
    query = Property.query.options(selectinload(Property.agent)).filter(Property.is_deleted.is_(False))

    # Text search
    if search_request.query:
        like = f"%{search_request.query}%"
        query = query.filter(
            (Property.title.ilike(like))
            | (Property.address.ilike(like))
            | (Property.description.ilike(like))
        )

    # Listing type filter
    if search_request.listing_type:
        query = query.filter(Property.listing_type == search_request.listing_type)

    # Status filter
    if search_request.status:
        query = query.filter(Property.status == search_request.status)

    # Property type filter
    if search_request.property_type:
        query = query.filter(Property.property_type == search_request.property_type)

    # Property category filter
    if search_request.property_category:
        query = query.filter(Property.property_category == search_request.property_category)

    # Neighborhood filter
    if search_request.neighborhood:
        query = query.filter(Property.neighborhood == search_request.neighborhood)

    # Price range filters
    if search_request.min_price is not None:
        query = query.filter(Property.price >= search_request.min_price)
    if search_request.max_price is not None:
        query = query.filter(Property.price <= search_request.max_price)

    # Bedrooms and bathrooms filters
    if search_request.bedrooms is not None:
        query = query.filter(Property.bedrooms >= search_request.bedrooms)
    if search_request.bathrooms is not None:
        query = query.filter(Property.bathrooms >= search_request.bathrooms)

    # Square footage filters
    if search_request.min_sqft is not None:
        query = query.filter(Property.square_feet >= search_request.min_sqft)
    if search_request.max_sqft is not None:
        query = query.filter(Property.square_feet <= search_request.max_sqft)

    # Year built filters
    if search_request.year_built_min is not None:
        query = query.filter(Property.year_built >= search_request.year_built_min)
    if search_request.year_built_max is not None:
        query = query.filter(Property.year_built <= search_request.year_built_max)

    # Agent ID filter
    if search_request.agent_id is not None:
        query = query.filter(Property.agent_id == search_request.agent_id)

    # Source filter
    if search_request.source:
        query = query.filter(Property.source == search_request.source)

    # Order by creation date descending (newest first)
    query = query.order_by(Property.created_at.desc())

    return query