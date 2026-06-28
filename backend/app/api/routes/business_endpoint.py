"""Business source CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.common_schema import ApiResponse, DeleteResponse, PageResponse
from backend.app.schemas.source_schema import (
    BusinessCreateRequest,
    BusinessQuery,
    BusinessResponse,
    BusinessUpdateRequest,
)
from backend.app.services.source_service import BusinessService

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post(
    "",
    response_model=ApiResponse[BusinessResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_business(request: BusinessCreateRequest, db: Session = Depends(get_db)):
    return ApiResponse[BusinessResponse](
        message="业务创建成功", data=BusinessService(db).create(request)
    )


@router.get("/{record_id}", response_model=ApiResponse[BusinessResponse])
def get_business(record_id: int, db: Session = Depends(get_db)):
    return ApiResponse[BusinessResponse](data=BusinessService(db).get(record_id))


@router.get("", response_model=ApiResponse[PageResponse[BusinessResponse]])
def page_businesses(
    query: Annotated[BusinessQuery, Query()], db: Session = Depends(get_db)
):
    return ApiResponse[PageResponse[BusinessResponse]](
        data=BusinessService(db).page(query)
    )


@router.patch("/{record_id}", response_model=ApiResponse[BusinessResponse])
def update_business(
    record_id: int, request: BusinessUpdateRequest, db: Session = Depends(get_db)
):
    return ApiResponse[BusinessResponse](
        message="业务更新成功", data=BusinessService(db).update(record_id, request)
    )


@router.delete("/{record_id}", response_model=ApiResponse[DeleteResponse])
def delete_business(record_id: int, db: Session = Depends(get_db)):
    BusinessService(db).delete(record_id)
    return ApiResponse[DeleteResponse](
        message="业务删除成功", data=DeleteResponse(id=record_id)
    )
