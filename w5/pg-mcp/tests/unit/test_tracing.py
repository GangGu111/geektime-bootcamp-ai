"""Unit tests for request trace context propagation and cleanup."""

import asyncio

import pytest

from pg_mcp.observability.tracing import get_request_id, request_context


@pytest.mark.asyncio
async def test_request_context_propagates_to_child_task_and_restores() -> None:
    assert get_request_id() is None

    async with request_context("outer-request"):
        assert get_request_id() == "outer-request"

        async def read_request_id() -> str | None:
            await asyncio.sleep(0)
            return get_request_id()

        assert await asyncio.create_task(read_request_id()) == "outer-request"

        async with request_context("inner-request"):
            assert get_request_id() == "inner-request"

        assert get_request_id() == "outer-request"

    assert get_request_id() is None
