from typing import Generic, Optional, Sequence, Type, TypeVar
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.database.session import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic base repository defining standard persistence operations."""

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: str) -> Optional[ModelType]:
        """Retrieve a single entity by its primary key."""
        return self.db.get(self.model, id)

    def list(self, offset: int = 0, limit: int = 20) -> Sequence[ModelType]:
        """Retrieve a paginated list of entities."""
        stmt = select(self.model).offset(offset).limit(limit)
        return self.db.scalars(stmt).all()

    def count(self) -> int:
        """Count total entities of this model."""
        stmt = select(func.count()).select_from(self.model)
        return self.db.scalar(stmt) or 0

    def create(self, entity: ModelType) -> ModelType:
        """Persist a new entity instance."""
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: ModelType) -> ModelType:
        """Commit updates to an existing entity instance."""
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: ModelType) -> None:
        """Delete an entity instance."""
        self.db.delete(entity)
        self.db.commit()
