"""Tests for the backend health endpoint."""

import asyncio

import httpx

from backend.app.main import app


async def get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_health_check() -> None:
    response = asyncio.run(get("/api/v1/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_is_available() -> None:
    response = asyncio.run(get("/openapi.json"))

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "QA Agent Forge API"
