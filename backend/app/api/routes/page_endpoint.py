"""Page source CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.common_schema import ApiResponse, DeleteResponse, PageResponse
from backend.app.schemas.source_schema import (
    PageCreateRequest,
    PageQuery,
    PageResponse as PageSourceResponse,
    PageUpdateRequest,
)
from backend.app.services.source_service import PageService

router = APIRouter(prefix="/pages", tags=["pages"])


@router.post(
    "",
    response_model=ApiResponse[PageSourceResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_page(request: PageCreateRequest, db: Session = Depends(get_db)):
    return ApiResponse[PageSourceResponse](
        message="页面创建成功", data=PageService(db).create(request)
    )


@router.get("/{record_id}", response_model=ApiResponse[PageSourceResponse])
def get_page(record_id: int, db: Session = Depends(get_db)):
    return ApiResponse[PageSourceResponse](data=PageService(db).get(record_id))


@router.get("", response_model=ApiResponse[PageResponse[PageSourceResponse]])
def page_pages(query: Annotated[PageQuery, Query()], db: Session = Depends(get_db)):
    return ApiResponse[PageResponse[PageSourceResponse]](
        data=PageService(db).page(query)
    )


@router.patch("/{record_id}", response_model=ApiResponse[PageSourceResponse])
def update_page(
    record_id: int, request: PageUpdateRequest, db: Session = Depends(get_db)
):
    return ApiResponse[PageSourceResponse](
        message="页面更新成功", data=PageService(db).update(record_id, request)
    )


@router.delete("/{record_id}", response_model=ApiResponse[DeleteResponse])
def delete_page(record_id: int, db: Session = Depends(get_db)):
    PageService(db).delete(record_id)
    return ApiResponse[DeleteResponse](
        message="页面删除成功", data=DeleteResponse(id=record_id)
    )
