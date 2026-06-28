"""Platform source CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.common_schema import ApiResponse, DeleteResponse, PageResponse
from backend.app.schemas.source_schema import (
    PlatformCreateRequest,
    PlatformQuery,
    PlatformResponse,
    PlatformUpdateRequest,
)
from backend.app.services.source_service import PlatformService

router = APIRouter(prefix="/platforms", tags=["platforms"])


@router.post(
    "",
    response_model=ApiResponse[PlatformResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_platform(request: PlatformCreateRequest, db: Session = Depends(get_db)):
    return ApiResponse[PlatformResponse](
        message="平台创建成功", data=PlatformService(db).create(request)
    )


@router.get("/{record_id}", response_model=ApiResponse[PlatformResponse])
def get_platform(record_id: int, db: Session = Depends(get_db)):
    return ApiResponse[PlatformResponse](data=PlatformService(db).get(record_id))


@router.get("", response_model=ApiResponse[PageResponse[PlatformResponse]])
def page_platforms(
    query: Annotated[PlatformQuery, Query()], db: Session = Depends(get_db)
):
    return ApiResponse[PageResponse[PlatformResponse]](
        data=PlatformService(db).page(query)
    )


@router.patch("/{record_id}", response_model=ApiResponse[PlatformResponse])
def update_platform(
    record_id: int, request: PlatformUpdateRequest, db: Session = Depends(get_db)
):
    return ApiResponse[PlatformResponse](
        message="平台更新成功", data=PlatformService(db).update(record_id, request)
    )


@router.delete("/{record_id}", response_model=ApiResponse[DeleteResponse])
def delete_platform(record_id: int, db: Session = Depends(get_db)):
    PlatformService(db).delete(record_id)
    return ApiResponse[DeleteResponse](
        message="平台删除成功", data=DeleteResponse(id=record_id)
    )
