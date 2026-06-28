"""System source CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.common_schema import ApiResponse, DeleteResponse, PageResponse
from backend.app.schemas.source_schema import (
    SystemCreateRequest,
    SystemQuery,
    SystemResponse,
    SystemUpdateRequest,
)
from backend.app.services.source_service import SystemService

router = APIRouter(prefix="/systems", tags=["systems"])


@router.post(
    "", response_model=ApiResponse[SystemResponse], status_code=status.HTTP_201_CREATED
)
def create_system(request: SystemCreateRequest, db: Session = Depends(get_db)):
    return ApiResponse[SystemResponse](
        message="系统创建成功", data=SystemService(db).create(request)
    )


@router.get("/{record_id}", response_model=ApiResponse[SystemResponse])
def get_system(record_id: int, db: Session = Depends(get_db)):
    return ApiResponse[SystemResponse](data=SystemService(db).get(record_id))


@router.get("", response_model=ApiResponse[PageResponse[SystemResponse]])
def page_systems(query: Annotated[SystemQuery, Query()], db: Session = Depends(get_db)):
    return ApiResponse[PageResponse[SystemResponse]](data=SystemService(db).page(query))


@router.patch("/{record_id}", response_model=ApiResponse[SystemResponse])
def update_system(
    record_id: int, request: SystemUpdateRequest, db: Session = Depends(get_db)
):
    return ApiResponse[SystemResponse](
        message="系统更新成功", data=SystemService(db).update(record_id, request)
    )


@router.delete("/{record_id}", response_model=ApiResponse[DeleteResponse])
def delete_system(record_id: int, db: Session = Depends(get_db)):
    SystemService(db).delete(record_id)
    return ApiResponse[DeleteResponse](
        message="系统删除成功", data=DeleteResponse(id=record_id)
    )
