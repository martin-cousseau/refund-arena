"""Remote MCP handshake must not take AgentOS down."""

from __future__ import annotations

import asyncio

import pytest

from app.tools import OptionalMCPTools, get_agno_docs_tools, get_parallel_tools


def test_agno_docs_tools_are_shared() -> None:
    assert get_agno_docs_tools()[0] is get_agno_docs_tools()[0]


def test_parallel_tools_are_shared() -> None:
    assert get_parallel_tools()[0] is get_parallel_tools()[0]


def test_optional_mcp_survives_anyio_cancel_scope() -> None:
    async def body() -> None:
        tools = OptionalMCPTools(
            url="https://example.invalid/mcp",
            transport="streamable-http",
            name="probe",
        )

        async def boom(force: bool = False) -> None:
            task = asyncio.current_task()
            assert task is not None
            task.cancel("Cancelled via cancel scope deadbeef")
            await asyncio.sleep(0)

        tools._connect = boom  # type: ignore[method-assign]
        await tools.connect()
        task = asyncio.current_task()
        assert task is not None
        assert task.cancelling() == 0

    asyncio.run(body())


def test_optional_mcp_reraises_real_cancellation() -> None:
    async def body() -> None:
        tools = OptionalMCPTools(
            url="https://example.invalid/mcp",
            transport="streamable-http",
            name="probe",
        )

        async def boom(force: bool = False) -> None:
            raise asyncio.CancelledError()

        tools._connect = boom  # type: ignore[method-assign]
        with pytest.raises(asyncio.CancelledError):
            await tools.connect()

    asyncio.run(body())


def test_optional_mcp_survives_exception_group() -> None:
    async def body() -> None:
        tools = OptionalMCPTools(
            url="https://example.invalid/mcp",
            transport="streamable-http",
            name="probe",
        )

        async def boom(force: bool = False) -> None:
            raise ExceptionGroup("unhandled errors in a TaskGroup", [RuntimeError("429")])

        tools._connect = boom  # type: ignore[method-assign]
        await tools.connect()

    asyncio.run(body())
