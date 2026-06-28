"""Application exceptions and FastAPI exception handlers."""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class BusinessException(Exception):
    """Expected domain error exposed through the API."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _error(
    status_code: int, code: str, message: str, data: object = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "code": code, "message": message, "data": data},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the backend's stable error response contract."""

    @app.exception_handler(BusinessException)
    async def business_exception_handler(
        _request: Request, exc: BusinessException
    ) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error(
            422,
            "VALIDATION_ERROR",
            "请求参数校验失败",
            jsonable_encoder(exc.errors()),
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(
        _request: Request, _exc: SQLAlchemyError
    ) -> JSONResponse:
        return _error(503, "DATABASE_ERROR", "数据库访问失败")
