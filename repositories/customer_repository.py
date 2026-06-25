from typing import List, Optional

from sqlalchemy import desc

from database import db
from repositories.base_repository import BaseRepository
from sqlalchemy_models import Customer


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self):
        super().__init__(Customer)

    def list_all(self) -> List[Customer]:
        return (
            db.session.query(Customer)
            .filter(Customer.is_deleted.is_(False))
            .order_by(Customer.name)
            .all()
        )

    def list_matchable(self, customer_ids: Optional[list[int]] = None, limit: Optional[int] = None) -> List[Customer]:
        query = db.session.query(Customer).filter(
            Customer.status.in_(["prospect", "active"]),
            Customer.is_deleted.is_(False),
        )
        if customer_ids:
            query = query.filter(Customer.id.in_(customer_ids))
        if limit:
            query = query.limit(limit)
        return query.order_by(desc(Customer.created_at)).all()

