"""Request, query and response schemas for source catalog resources."""

from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceResponse(SourceSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    remark: str | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class QueryBase(SourceSchema):
    id: int | None = Field(default=None, ge=1)
    remark: str | None = None
    is_deleted: bool = False
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
    updated_at_from: datetime | None = None
    updated_at_to: datetime | None = None
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = "id"
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")

    @model_validator(mode="after")
    def validate_ranges(self) -> "QueryBase":
        if self.created_at_from and self.created_at_to:
            if self.created_at_from > self.created_at_to:
                raise ValueError("created_at_from 不能晚于 created_at_to")
        if self.updated_at_from and self.updated_at_to:
            if self.updated_at_from > self.updated_at_to:
                raise ValueError("updated_at_from 不能晚于 updated_at_to")
        return self


class UpdateBase(SourceSchema):
    non_nullable_fields: ClassVar[set[str]] = set()

    @model_validator(mode="after")
    def require_update_field(self) -> "UpdateBase":
        if not self.model_fields_set:
            raise ValueError("至少需要提供一个可修改字段")
        invalid_nulls = self.non_nullable_fields.intersection(self.model_fields_set)
        invalid_nulls = {
            field for field in invalid_nulls if getattr(self, field) is None
        }
        if invalid_nulls:
            raise ValueError(f"以下字段不能为 null: {', '.join(sorted(invalid_nulls))}")
        return self


class CompanyCreateRequest(SourceSchema):
    company_code: str | None = Field(default=None, max_length=64)
    company_name: str = Field(min_length=1, max_length=128)
    remark: str | None = Field(default=None, max_length=500)


class CompanyUpdateRequest(UpdateBase):
    non_nullable_fields = {"company_name"}
    company_code: str | None = Field(default=None, max_length=64)
    company_name: str | None = Field(default=None, min_length=1, max_length=128)
    remark: str | None = Field(default=None, max_length=500)


class CompanyQuery(QueryBase):
    company_code: str | None = None
    company_name: str | None = None


class CompanyResponse(SourceResponse):
    company_code: str | None
    company_name: str


class BusinessCreateRequest(SourceSchema):
    company_id: int = Field(ge=1)
    business_code: str | None = Field(default=None, max_length=64)
    business_name: str = Field(min_length=1, max_length=128)
    remark: str | None = Field(default=None, max_length=500)


class BusinessUpdateRequest(UpdateBase):
    non_nullable_fields = {"company_id", "business_name"}
    company_id: int | None = Field(default=None, ge=1)
    business_code: str | None = Field(default=None, max_length=64)
    business_name: str | None = Field(default=None, min_length=1, max_length=128)
    remark: str | None = Field(default=None, max_length=500)


class BusinessQuery(QueryBase):
    company_id: int | None = Field(default=None, ge=1)
    business_code: str | None = None
    business_name: str | None = None


class BusinessResponse(SourceResponse):
    company_id: int
    business_code: str | None
    business_name: str


class PlatformCreateRequest(SourceSchema):
    company_id: int = Field(ge=1)
    business_id: int = Field(ge=1)
    platform_code: str = Field(min_length=1, max_length=64)
    platform_name: str = Field(min_length=1, max_length=128)
    platform_type: str | None = Field(default=None, max_length=64)
    platform_url: str | None = Field(default=None, max_length=500)
    owner: str | None = Field(default=None, max_length=128)
    remark: str | None = Field(default=None, max_length=500)


class PlatformUpdateRequest(UpdateBase):
    non_nullable_fields = {
        "company_id",
        "business_id",
        "platform_code",
        "platform_name",
    }
    company_id: int | None = Field(default=None, ge=1)
    business_id: int | None = Field(default=None, ge=1)
    platform_code: str | None = Field(default=None, min_length=1, max_length=64)
    platform_name: str | None = Field(default=None, min_length=1, max_length=128)
    platform_type: str | None = Field(default=None, max_length=64)
    platform_url: str | None = Field(default=None, max_length=500)
    owner: str | None = Field(default=None, max_length=128)
    remark: str | None = Field(default=None, max_length=500)


class PlatformQuery(QueryBase):
    company_id: int | None = Field(default=None, ge=1)
    business_id: int | None = Field(default=None, ge=1)
    platform_code: str | None = None
    platform_name: str | None = None
    platform_type: str | None = None
    platform_url: str | None = None
    owner: str | None = None


class PlatformResponse(SourceResponse):
    company_id: int
    business_id: int
    platform_code: str
    platform_name: str
    platform_type: str | None
    platform_url: str | None
    owner: str | None


class SystemCreateRequest(SourceSchema):
    company_id: int = Field(ge=1)
    business_id: int = Field(ge=1)
    system_code: str | None = Field(default=None, max_length=64)
    system_name: str = Field(min_length=1, max_length=128)
    platform_id: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=500)


class SystemUpdateRequest(UpdateBase):
    non_nullable_fields = {"company_id", "business_id", "system_name"}
    company_id: int | None = Field(default=None, ge=1)
    business_id: int | None = Field(default=None, ge=1)
    system_code: str | None = Field(default=None, max_length=64)
    system_name: str | None = Field(default=None, min_length=1, max_length=128)
    platform_id: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=500)


class SystemQuery(QueryBase):
    company_id: int | None = Field(default=None, ge=1)
    business_id: int | None = Field(default=None, ge=1)
    system_code: str | None = None
    system_name: str | None = None
    platform_id: int | None = Field(default=None, ge=1)


class SystemResponse(SourceResponse):
    company_id: int
    business_id: int
    system_code: str | None
    system_name: str
    platform_id: int | None


class PageCreateRequest(SourceSchema):
    company_id: int = Field(ge=1)
    business_id: int = Field(ge=1)
    system_id: int = Field(ge=1)
    page_code: str | None = Field(default=None, max_length=64)
    page_name: str = Field(min_length=1, max_length=128)
    page_path: str | None = Field(default=None, max_length=500)
    remark: str | None = Field(default=None, max_length=500)


class PageUpdateRequest(UpdateBase):
    non_nullable_fields = {"company_id", "business_id", "system_id", "page_name"}
    company_id: int | None = Field(default=None, ge=1)
    business_id: int | None = Field(default=None, ge=1)
    system_id: int | None = Field(default=None, ge=1)
    page_code: str | None = Field(default=None, max_length=64)
    page_name: str | None = Field(default=None, min_length=1, max_length=128)
    page_path: str | None = Field(default=None, max_length=500)
    remark: str | None = Field(default=None, max_length=500)


class PageQuery(QueryBase):
    company_id: int | None = Field(default=None, ge=1)
    business_id: int | None = Field(default=None, ge=1)
    system_id: int | None = Field(default=None, ge=1)
    page_code: str | None = None
    page_name: str | None = None
    page_path: str | None = None


class PageResponse(SourceResponse):
    company_id: int
    business_id: int
    system_id: int
    page_code: str | None
    page_name: str
    page_path: str | None
