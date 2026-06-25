from typing import List, Optional

from sqlalchemy import desc, or_
from sqlalchemy.orm import selectinload

from database import db
from repositories.base_repository import BaseRepository
from sqlalchemy_models import Property


class PropertyRepository(BaseRepository[Property]):
    def __init__(self):
        super().__init__(Property)

    def list_filtered(
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
        query = (
            db.session.query(Property)
            .options(selectinload(Property.agent))
            .filter(Property.is_deleted.is_(False))
        )

        if search:
            query = query.filter(
                or_(
                    Property.title.ilike(f"%{search}%"),
                    Property.address.ilike(f"%{search}%"),
                    Property.description.ilike(f"%{search}%"),
                )
            )

        if status:
            query = query.filter(Property.status == status)
        if property_type:
            query = query.filter(Property.property_type == property_type)
        if property_category:
            query = query.filter(Property.property_category == property_category)
        if property_condition:
            query = query.filter(Property.property_condition == property_condition)
        if neighborhood:
            query = query.filter(Property.neighborhood == neighborhood)
        if listing_type:
            query = query.filter(Property.listing_type == listing_type)
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

    def list_active(self, limit: Optional[int] = None) -> List[Property]:
        query = db.session.query(Property).filter(
            Property.status == "active",
            Property.is_deleted.is_(False),
        )
        if limit:
            query = query.limit(limit)
        return query.order_by(desc(Property.updated_at)).all()

