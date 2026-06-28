"""Company source CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.common_schema import ApiResponse, DeleteResponse, PageResponse
from backend.app.schemas.source_schema import (
    CompanyCreateRequest,
    CompanyQuery,
    CompanyResponse,
    CompanyUpdateRequest,
)
from backend.app.services.source_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post(
    "", response_model=ApiResponse[CompanyResponse], status_code=status.HTTP_201_CREATED
)
def create_company(request: CompanyCreateRequest, db: Session = Depends(get_db)):
    return ApiResponse[CompanyResponse](
        message="公司创建成功", data=CompanyService(db).create(request)
    )


@router.get("/{record_id}", response_model=ApiResponse[CompanyResponse])
def get_company(record_id: int, db: Session = Depends(get_db)):
    return ApiResponse[CompanyResponse](data=CompanyService(db).get(record_id))


@router.get("", response_model=ApiResponse[PageResponse[CompanyResponse]])
def page_companies(
    query: Annotated[CompanyQuery, Query()], db: Session = Depends(get_db)
):
    return ApiResponse[PageResponse[CompanyResponse]](
        data=CompanyService(db).page(query)
    )


@router.patch("/{record_id}", response_model=ApiResponse[CompanyResponse])
def update_company(
    record_id: int, request: CompanyUpdateRequest, db: Session = Depends(get_db)
):
    return ApiResponse[CompanyResponse](
        message="公司更新成功", data=CompanyService(db).update(record_id, request)
    )


@router.delete("/{record_id}", response_model=ApiResponse[DeleteResponse])
def delete_company(record_id: int, db: Session = Depends(get_db)):
    CompanyService(db).delete(record_id)
    return ApiResponse[DeleteResponse](
        message="公司删除成功", data=DeleteResponse(id=record_id)
    )
