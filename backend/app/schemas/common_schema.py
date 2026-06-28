"""Shared API response and pagination schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "操作成功"
    data: T | None = None


class PageResponse(BaseModel, Generic[T]):
    total: int
    page_no: int
    page_size: int
    records: list[T]


class DeleteResponse(BaseModel):
    id: int


class PaginationQuery(BaseModel):
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = "id"
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
