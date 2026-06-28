"""Database access for source catalog resources."""

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.source_model import (
    BusinessSourceModel,
    CompanySourceModel,
    PageSourceModel,
    PlatformSourceModel,
    SystemSourceModel,
    TimestampedSourceModel,
)

ModelT = TypeVar("ModelT", bound=TimestampedSourceModel)


class SourceRepository(Generic[ModelT]):
    """Reusable persistence operations shared by the five source tables."""

    def __init__(self, db: Session, model: type[ModelT]) -> None:
        self.db = db
        self.model = model

    def get(self, record_id: int, *, include_deleted: bool = False) -> ModelT | None:
        statement = select(self.model).where(self.model.id == record_id)
        if not include_deleted:
            statement = statement.where(self.model.is_deleted == 0)
        return self.db.scalar(statement)

    def find_one(self, **conditions: Any) -> ModelT | None:
        statement = select(self.model).where(self.model.is_deleted == 0)
        for field, value in conditions.items():
            statement = statement.where(getattr(self.model, field) == value)
        return self.db.scalar(statement.limit(1))

    def count_active(self, **conditions: Any) -> int:
        statement = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.is_deleted == 0)
        )
        for field, value in conditions.items():
            statement = statement.where(getattr(self.model, field) == value)
        return int(self.db.scalar(statement) or 0)

    def page(
        self,
        filters: dict[str, Any],
        *,
        fuzzy_fields: set[str],
        page_no: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[int, list[ModelT]]:
        conditions = []
        range_fields = {
            "created_at_from": ("created_at", ">="),
            "created_at_to": ("created_at", "<="),
            "updated_at_from": ("updated_at", ">="),
            "updated_at_to": ("updated_at", "<="),
        }
        for field, value in filters.items():
            if value is None:
                continue
            if field in range_fields:
                column_name, operator = range_fields[field]
                column = getattr(self.model, column_name)
                conditions.append(
                    column >= value if operator == ">=" else column <= value
                )
            elif field in fuzzy_fields:
                conditions.append(
                    getattr(self.model, field).contains(value, autoescape=True)
                )
            else:
                conditions.append(getattr(self.model, field) == value)

        count_statement = (
            select(func.count()).select_from(self.model).where(*conditions)
        )
        total = int(self.db.scalar(count_statement) or 0)
        sort_column = getattr(self.model, sort_by)
        ordering = sort_column.asc() if sort_order == "asc" else sort_column.desc()
        statement = (
            select(self.model)
            .where(*conditions)
            .order_by(ordering, self.model.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        return total, list(self.db.scalars(statement).all())

    def create(self, data: dict[str, Any]) -> ModelT:
        record = self.model(**data)
        self.db.add(record)
        self.db.flush()
        return record

    def update(self, record: ModelT, data: dict[str, Any]) -> ModelT:
        for field, value in data.items():
            setattr(record, field, value)
        self.db.flush()
        return record

    def soft_delete(self, record: ModelT) -> None:
        record.is_deleted = 1
        self.db.flush()


class CompanyRepository(SourceRepository[CompanySourceModel]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, CompanySourceModel)


class BusinessRepository(SourceRepository[BusinessSourceModel]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, BusinessSourceModel)


class PlatformRepository(SourceRepository[PlatformSourceModel]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, PlatformSourceModel)


class SystemRepository(SourceRepository[SystemSourceModel]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, SystemSourceModel)


class PageRepository(SourceRepository[PageSourceModel]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, PageSourceModel)
