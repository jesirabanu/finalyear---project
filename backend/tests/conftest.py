"""Pytest configuration and shared fixtures for asynchronous backend testing.
"""
from typing import AsyncGenerator
import httpx
import pytest_asyncio
from app.main import app


class ApiTestClient(httpx.AsyncClient):
    """An AsyncClient for API testing whose HTTP verb methods (get, post, etc.)
    are defined on the subclass so that mock.patch('httpx.AsyncClient.get') or
    mock.patch('httpx.AsyncClient.post') targeting internal service calls do NOT
    intercept test client calls to the FastAPI ASGI application.
    """
    async def get(self, url, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url, **kwargs) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url, **kwargs) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)

    async def patch(self, url, **kwargs) -> httpx.Response:
        return await self.request("PATCH", url, **kwargs)


@pytest_asyncio.fixture(loop_scope="function")
async def async_client() -> AsyncGenerator[ApiTestClient, None]:
    """Asynchronous HTTP test client bound to FastAPI application via ASGITransport."""
    async with ApiTestClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
