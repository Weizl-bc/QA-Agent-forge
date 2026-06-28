"""Business rules and transaction boundaries for source catalog CRUD."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.exception import BusinessException
from backend.app.models.source_model import TimestampedSourceModel
from backend.app.repositories.source_repository import (
    BusinessRepository,
    CompanyRepository,
    PageRepository,
    PlatformRepository,
    SourceRepository,
    SystemRepository,
)
from backend.app.schemas.common_schema import PageResponse

ModelT = TypeVar("ModelT", bound=TimestampedSourceModel)


class SourceService(Generic[ModelT]):
    resource_name = "记录"
    fuzzy_fields: set[str] = {"remark"}
    sortable_fields: set[str] = {"id", "created_at", "updated_at"}

    def __init__(self, db: Session, repository: SourceRepository[ModelT]) -> None:
        self.db = db
        self.repository = repository

    def get(self, record_id: int) -> ModelT:
        record = self.repository.get(record_id)
        if record is None:
            raise BusinessException(404, "NOT_FOUND", f"{self.resource_name}不存在")
        return record

    def page(self, query: BaseModel) -> PageResponse[Any]:
        values = query.model_dump()
        page_no = values.pop("page_no")
        page_size = values.pop("page_size")
        sort_by = values.pop("sort_by")
        sort_order = values.pop("sort_order")
        if sort_by not in self.sortable_fields:
            allowed = ", ".join(sorted(self.sortable_fields))
            raise BusinessException(
                422, "VALIDATION_ERROR", f"sort_by 仅支持: {allowed}"
            )
        total, records = self.repository.page(
            values,
            fuzzy_fields=self.fuzzy_fields,
            page_no=page_no,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return PageResponse[Any](
            total=total, page_no=page_no, page_size=page_size, records=records
        )

    def create(self, request: BaseModel) -> ModelT:
        data = request.model_dump()
        self._validate_relations(data)
        self._validate_unique(data)
        try:
            record = self.repository.create(data)
            self.db.commit()
            self.db.refresh(record)
            return record
        except IntegrityError as exc:
            self.db.rollback()
            raise BusinessException(409, "CONFLICT", "数据违反唯一性约束") from exc
        except Exception:
            self.db.rollback()
            raise

    def update(self, record_id: int, request: BaseModel) -> ModelT:
        record = self.get(record_id)
        changes = request.model_dump(exclude_unset=True)
        proposed = {
            column.name: getattr(record, column.name)
            for column in record.__table__.columns
        }
        proposed.update(changes)
        self._validate_update(record, proposed, changes)
        self._validate_relations(proposed)
        self._validate_unique(proposed, exclude_id=record_id)
        try:
            self.repository.update(record, changes)
            self.db.commit()
            self.db.refresh(record)
            return record
        except IntegrityError as exc:
            self.db.rollback()
            raise BusinessException(409, "CONFLICT", "数据违反唯一性约束") from exc
        except Exception:
            self.db.rollback()
            raise

    def delete(self, record_id: int) -> None:
        record = self.get(record_id)
        self._validate_delete(record)
        try:
            self.repository.soft_delete(record)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _validate_relations(self, data: dict[str, Any]) -> None:
        return None

    def _validate_unique(
        self, data: dict[str, Any], *, exclude_id: int | None = None
    ) -> None:
        return None

    def _validate_update(
        self, record: ModelT, proposed: dict[str, Any], changes: dict[str, Any]
    ) -> None:
        return None

    def _validate_delete(self, record: ModelT) -> None:
        return None

    def _require_company(self, company_id: int) -> None:
        if CompanyRepository(self.db).get(company_id) is None:
            raise BusinessException(409, "RELATION_CONFLICT", "关联公司不存在或已删除")

    def _require_business(self, business_id: int, company_id: int) -> None:
        business = BusinessRepository(self.db).get(business_id)
        if business is None or business.company_id != company_id:
            raise BusinessException(
                409, "RELATION_CONFLICT", "关联业务不存在、已删除或不属于该公司"
            )

    def _require_platform(
        self, platform_id: int | None, company_id: int, business_id: int
    ) -> None:
        if platform_id is None:
            return
        platform = PlatformRepository(self.db).get(platform_id)
        if (
            platform is None
            or platform.company_id != company_id
            or platform.business_id != business_id
        ):
            raise BusinessException(
                409, "RELATION_CONFLICT", "关联平台不存在、已删除或层级不匹配"
            )

    def _require_system(
        self, system_id: int, company_id: int, business_id: int
    ) -> None:
        system = SystemRepository(self.db).get(system_id)
        if (
            system is None
            or system.company_id != company_id
            or system.business_id != business_id
        ):
            raise BusinessException(
                409, "RELATION_CONFLICT", "关联系统不存在、已删除或层级不匹配"
            )

    @staticmethod
    def _reject_if_referenced(count: int, message: str) -> None:
        if count:
            raise BusinessException(409, "RESOURCE_IN_USE", message)


class CompanyService(SourceService):
    resource_name = "公司"
    fuzzy_fields = {"company_name", "remark"}
    sortable_fields = SourceService.sortable_fields | {"company_code", "company_name"}

    def __init__(self, db: Session) -> None:
        super().__init__(db, CompanyRepository(db))

    def _validate_delete(self, record: ModelT) -> None:
        references = sum(
            repository.count_active(company_id=record.id)
            for repository in (
                BusinessRepository(self.db),
                PlatformRepository(self.db),
                SystemRepository(self.db),
                PageRepository(self.db),
            )
        )
        self._reject_if_referenced(references, "公司仍被有效下级数据引用")


class BusinessService(SourceService):
    resource_name = "业务"
    fuzzy_fields = {"business_name", "remark"}
    sortable_fields = SourceService.sortable_fields | {"business_code", "business_name"}

    def __init__(self, db: Session) -> None:
        super().__init__(db, BusinessRepository(db))

    def _validate_relations(self, data: dict[str, Any]) -> None:
        self._require_company(data["company_id"])

    def _reference_count(self, business_id: int) -> int:
        return sum(
            repository.count_active(business_id=business_id)
            for repository in (
                PlatformRepository(self.db),
                SystemRepository(self.db),
                PageRepository(self.db),
            )
        )

    def _validate_update(
        self, record: ModelT, proposed: dict[str, Any], changes: dict[str, Any]
    ) -> None:
        if "company_id" in changes and changes["company_id"] != record.company_id:
            self._reject_if_referenced(
                self._reference_count(record.id),
                "业务仍被有效下级数据引用，不能修改所属公司",
            )

    def _validate_delete(self, record: ModelT) -> None:
        self._reject_if_referenced(
            self._reference_count(record.id), "业务仍被有效下级数据引用"
        )


class PlatformService(SourceService):
    resource_name = "平台"
    fuzzy_fields = {"platform_name", "platform_url", "owner", "remark"}
    sortable_fields = SourceService.sortable_fields | {"platform_code", "platform_name"}

    def __init__(self, db: Session) -> None:
        super().__init__(db, PlatformRepository(db))

    def _validate_relations(self, data: dict[str, Any]) -> None:
        self._require_company(data["company_id"])
        self._require_business(data["business_id"], data["company_id"])

    def _validate_unique(
        self, data: dict[str, Any], *, exclude_id: int | None = None
    ) -> None:
        duplicate = PlatformRepository(self.db).find_one(
            company_id=data["company_id"],
            business_id=data["business_id"],
            platform_code=data["platform_code"],
        )
        if duplicate is not None and duplicate.id != exclude_id:
            raise BusinessException(409, "CONFLICT", "同一公司和业务下的平台编码已存在")

    def _validate_update(
        self, record: ModelT, proposed: dict[str, Any], changes: dict[str, Any]
    ) -> None:
        hierarchy_changed = any(
            field in changes and changes[field] != getattr(record, field)
            for field in ("company_id", "business_id")
        )
        if hierarchy_changed:
            self._reject_if_referenced(
                SystemRepository(self.db).count_active(platform_id=record.id),
                "平台仍被有效系统引用，不能修改所属层级",
            )

    def _validate_delete(self, record: ModelT) -> None:
        self._reject_if_referenced(
            SystemRepository(self.db).count_active(platform_id=record.id),
            "平台仍被有效系统引用",
        )


class SystemService(SourceService):
    resource_name = "系统"
    fuzzy_fields = {"system_name", "remark"}
    sortable_fields = SourceService.sortable_fields | {"system_code", "system_name"}

    def __init__(self, db: Session) -> None:
        super().__init__(db, SystemRepository(db))

    def _validate_relations(self, data: dict[str, Any]) -> None:
        self._require_company(data["company_id"])
        self._require_business(data["business_id"], data["company_id"])
        self._require_platform(
            data.get("platform_id"), data["company_id"], data["business_id"]
        )

    def _validate_update(
        self, record: ModelT, proposed: dict[str, Any], changes: dict[str, Any]
    ) -> None:
        hierarchy_changed = any(
            field in changes and changes[field] != getattr(record, field)
            for field in ("company_id", "business_id")
        )
        if hierarchy_changed:
            self._reject_if_referenced(
                PageRepository(self.db).count_active(system_id=record.id),
                "系统仍被有效页面引用，不能修改所属层级",
            )

    def _validate_delete(self, record: ModelT) -> None:
        self._reject_if_referenced(
            PageRepository(self.db).count_active(system_id=record.id),
            "系统仍被有效页面引用",
        )


class PageService(SourceService):
    resource_name = "页面"
    fuzzy_fields = {"page_name", "page_path", "remark"}
    sortable_fields = SourceService.sortable_fields | {"page_code", "page_name"}

    def __init__(self, db: Session) -> None:
        super().__init__(db, PageRepository(db))

    def _validate_relations(self, data: dict[str, Any]) -> None:
        self._require_company(data["company_id"])
        self._require_business(data["business_id"], data["company_id"])
        self._require_system(data["system_id"], data["company_id"], data["business_id"])
