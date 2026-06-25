from datetime import datetime
from typing import Generic, Optional, TypeVar

from database import db


ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, model):
        self.model = model

    def get_by_id(self, entity_id: int) -> Optional[ModelType]:
        query = db.session.query(self.model).filter(self.model.id == entity_id)
        is_deleted_col = getattr(self.model, "is_deleted", None)
        if is_deleted_col is not None:
            query = query.filter(is_deleted_col.is_(False))
        return query.first()

    def save(self, entity: ModelType) -> ModelType:
        db.session.add(entity)
        db.session.commit()
        return entity

    def soft_delete(self, entity_id: int) -> bool:
        entity = self.get_by_id(entity_id)
        if not entity:
            return False
        setattr(entity, "is_deleted", True)
        setattr(entity, "deleted_at", datetime.utcnow())
        db.session.commit()
        return True
