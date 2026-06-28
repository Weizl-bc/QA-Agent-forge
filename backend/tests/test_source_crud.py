"""API tests for source catalog CRUD and hierarchy rules."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app


@asynccontextmanager
async def isolated_client() -> AsyncIterator[httpx.AsyncClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()


async def create_hierarchy(client: httpx.AsyncClient) -> dict[str, int]:
    company = await client.post(
        "/api/v1/companies",
        json={"company_code": "COMP", "company_name": "测试公司"},
    )
    assert company.status_code == 201
    company_id = company.json()["data"]["id"]

    business = await client.post(
        "/api/v1/businesses",
        json={
            "company_id": company_id,
            "business_code": "BIZ",
            "business_name": "测试业务",
        },
    )
    assert business.status_code == 201
    business_id = business.json()["data"]["id"]

    platform = await client.post(
        "/api/v1/platforms",
        json={
            "company_id": company_id,
            "business_id": business_id,
            "platform_code": "WEB",
            "platform_name": "Web 平台",
        },
    )
    assert platform.status_code == 201
    platform_id = platform.json()["data"]["id"]

    system = await client.post(
        "/api/v1/systems",
        json={
            "company_id": company_id,
            "business_id": business_id,
            "platform_id": platform_id,
            "system_code": "OMS",
            "system_name": "订单系统",
        },
    )
    assert system.status_code == 201
    system_id = system.json()["data"]["id"]

    page = await client.post(
        "/api/v1/pages",
        json={
            "company_id": company_id,
            "business_id": business_id,
            "system_id": system_id,
            "page_code": "ORDER_LIST",
            "page_name": "订单列表",
            "page_path": "/orders",
        },
    )
    assert page.status_code == 201
    return {
        "company": company_id,
        "business": business_id,
        "platform": platform_id,
        "system": system_id,
        "page": page.json()["data"]["id"],
    }


def test_complete_crud_pagination_and_soft_delete() -> None:
    async def scenario() -> None:
        async with isolated_client() as client:
            ids = await create_hierarchy(client)

            update_cases = (
                ("companies", "company", {"company_name": "更新后的公司"}),
                ("businesses", "business", {"business_name": "更新后的业务"}),
                ("platforms", "platform", {"owner": "测试负责人"}),
                ("systems", "system", {"remark": "系统备注"}),
            )
            for resource_path, id_key, payload in update_cases:
                detail = await client.get(f"/api/v1/{resource_path}/{ids[id_key]}")
                assert detail.status_code == 200
                updated_resource = await client.patch(
                    f"/api/v1/{resource_path}/{ids[id_key]}", json=payload
                )
                assert updated_resource.status_code == 200
                for field, value in payload.items():
                    assert updated_resource.json()["data"][field] == value

            page = await client.get(
                "/api/v1/pages",
                params={"page_name": "订单", "page_no": 1, "page_size": 1},
            )
            assert page.status_code == 200
            assert page.json()["data"]["total"] == 1
            assert len(page.json()["data"]["records"]) == 1

            updated = await client.patch(
                f"/api/v1/pages/{ids['page']}", json={"remark": "已更新"}
            )
            assert updated.status_code == 200
            assert updated.json()["data"]["remark"] == "已更新"

            deleted = await client.delete(f"/api/v1/pages/{ids['page']}")
            assert deleted.status_code == 200
            assert (await client.get(f"/api/v1/pages/{ids['page']}")).status_code == 404

            active = await client.get("/api/v1/pages")
            removed = await client.get("/api/v1/pages", params={"is_deleted": "true"})
            assert active.json()["data"]["total"] == 0
            assert removed.json()["data"]["total"] == 1

            resource_paths = {
                "system": "systems",
                "platform": "platforms",
                "business": "businesses",
                "company": "companies",
            }
            for resource, resource_path in resource_paths.items():
                path = f"/api/v1/{resource_path}/{ids[resource]}"
                assert (await client.delete(path)).status_code == 200

    asyncio.run(scenario())


def test_relationship_conflicts_and_parent_protection() -> None:
    async def scenario() -> None:
        async with isolated_client() as client:
            ids = await create_hierarchy(client)

            invalid = await client.post(
                "/api/v1/businesses",
                json={"company_id": 9999, "business_name": "无效业务"},
            )
            assert invalid.status_code == 409
            assert invalid.json()["code"] == "RELATION_CONFLICT"

            protected = await client.delete(f"/api/v1/companies/{ids['company']}")
            assert protected.status_code == 409
            assert protected.json()["code"] == "RESOURCE_IN_USE"

            changed = await client.patch(
                f"/api/v1/businesses/{ids['business']}", json={"company_id": 9999}
            )
            assert changed.status_code == 409

    asyncio.run(scenario())


def test_unique_platform_validation_and_error_contract() -> None:
    async def scenario() -> None:
        async with isolated_client() as client:
            ids = await create_hierarchy(client)
            duplicate = await client.post(
                "/api/v1/platforms",
                json={
                    "company_id": ids["company"],
                    "business_id": ids["business"],
                    "platform_code": "WEB",
                    "platform_name": "重复平台",
                },
            )
            assert duplicate.status_code == 409
            assert duplicate.json()["success"] is False

            empty_patch = await client.patch(f"/api/v1/pages/{ids['page']}", json={})
            assert empty_patch.status_code == 422
            assert empty_patch.json()["code"] == "VALIDATION_ERROR"

            invalid_sort = await client.get(
                "/api/v1/pages", params={"sort_by": "unknown_column"}
            )
            assert invalid_sort.status_code == 422
            assert invalid_sort.json()["success"] is False

    asyncio.run(scenario())
