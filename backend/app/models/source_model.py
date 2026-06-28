"""Mappings for the five RAG source catalog tables."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, SmallInteger, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class TimestampedSourceModel:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_deleted: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )


class CompanySourceModel(TimestampedSourceModel, Base):
    __tablename__ = "rag_company_source"

    company_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_name: Mapped[str] = mapped_column(String(128), nullable=False)


class BusinessSourceModel(TimestampedSourceModel, Base):
    __tablename__ = "rag_business_source"

    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    business_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    business_name: Mapped[str] = mapped_column(String(128), nullable=False)


class PlatformSourceModel(TimestampedSourceModel, Base):
    __tablename__ = "rag_platform_source"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "business_id", "platform_code", name="uk_platform_code"
        ),
    )

    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    business_id: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_code: Mapped[str] = mapped_column(String(64), nullable=False)
    platform_name: Mapped[str] = mapped_column(String(128), nullable=False)
    platform_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)


class SystemSourceModel(TimestampedSourceModel, Base):
    __tablename__ = "rag_system_source"

    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    business_id: Mapped[int] = mapped_column(Integer, nullable=False)
    system_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    system_name: Mapped[str] = mapped_column(String(128), nullable=False)
    platform_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PageSourceModel(TimestampedSourceModel, Base):
    __tablename__ = "rag_page_source"

    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    business_id: Mapped[int] = mapped_column(Integer, nullable=False)
    system_id: Mapped[int] = mapped_column(Integer, nullable=False)
    page_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page_name: Mapped[str] = mapped_column(String(128), nullable=False)
    page_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
