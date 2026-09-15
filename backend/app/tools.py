"""
Platform Tools
==============
"""

from __future__ import annotations

import asyncio
from os import getenv

from agno.tools.file import FileGenerationTools
from agno.tools.knowledge import KnowledgeManagementTools
from agno.tools.mcp import MCPTools
from agno.tools.openai import OpenAITools
from agno.tools.parallel import ParallelTools
from agno.tools.slack import SlackTools
from agno.utils.log import log_warning

from app.knowledge import product_knowledge

AGNO_DOCS_MCP_URL = "https://docs.agno.com/mcp"


def _is_anyio_cancel_scope(exc: BaseException) -> bool:
    """True when anyio cancelled the host task because an MCP child request failed.

    The streamable-http client runs the POST in a task group. A 429/5xx there
    cancels the AgentOS lifespan task with ``Cancelled via cancel scope …``.
    MCPTools.connect() only catches Exception, so that CancelledError used to
    abort uvicorn (SystemExit 3) plus a follow-on cancel-scope RuntimeError.
    """
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, asyncio.CancelledError) and current.args:
            msg = current.args[0]
            if isinstance(msg, str) and msg.startswith("Cancelled via cancel scope "):
                return True
        ctx = current.__context__
        current = ctx if isinstance(ctx, BaseException) else None
    return False


class OptionalMCPTools(MCPTools):
    """MCP toolkit whose failed handshake never fails AgentOS startup."""

    async def connect(self, force: bool = False) -> None:
        try:
            await super().connect(force=force)
        except (KeyboardInterrupt, SystemExit):
            raise
        except asyncio.CancelledError as exc:
            if not _is_anyio_cancel_scope(exc):
                raise
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                task.uncancel()
            await self._abandon(exc)
        except BaseException as exc:
            await self._abandon(exc)

    async def _abandon(self, exc: BaseException) -> None:
        log_warning(f"MCP {self.name} unavailable ({type(exc).__name__}: {exc}); continuing without it")
        try:
            await self._safe_cleanup()
        except BaseException:
            pass


_agno_docs_tools: MCPTools | None = None
_parallel_tools: ParallelTools | MCPTools | None = None


def get_agno_docs_tools() -> list[MCPTools]:
    # One instance shared by Platform Builder and the registry — AgentOS connects
    # every distinct MCPTools object on boot, and docs.agno.com rate-limits duplicates.
    global _agno_docs_tools
    if _agno_docs_tools is None:
        _agno_docs_tools = OptionalMCPTools(
            transport="streamable-http",
            url=AGNO_DOCS_MCP_URL,
            name="agno_docs",
            refresh_connection=True,
        )
    return [_agno_docs_tools]


def get_parallel_tools() -> list[ParallelTools | MCPTools]:
    global _parallel_tools
    if _parallel_tools is None:
        if getenv("PARALLEL_API_KEY"):
            _parallel_tools = ParallelTools()
        else:
            # timeout_seconds: web_fetch page extraction regularly exceeds the 10s MCP default.
            _parallel_tools = OptionalMCPTools(
                url="https://search.parallel.ai/mcp",
                transport="streamable-http",
                name="parallel_tools",
                timeout_seconds=30,
                refresh_connection=True,
            )
    return [_parallel_tools]


def get_slack_tools() -> list[SlackTools]:
    """Send-scoped Slack toolkit, only when the Slack interface is configured.

    Deliberately narrower than the SlackTools defaults: a registry any agent
    can draw from gets post + channel listing, never history reads or file transfer.
    """
    if not getenv("SLACK_BOT_TOKEN"):
        return []
    return [
        SlackTools(
            token=getenv("SLACK_BOT_TOKEN"),
            enable_send_message=True,
            enable_send_message_thread=True,
            enable_list_channels=True,
            enable_get_channel_history=False,
            enable_upload_file=False,
            enable_download_file=False,
        )
    ]


def get_media_tools() -> list[OpenAITools]:
    """Image generation and text-to-speech. Optional: needs OPENAI_API_KEY.

    Models and embeddings do not use this key. Generated media come back as run
    artifacts (bytes on the RunResponse), so they persist in Postgres and survive
    ephemeral container filesystems. Transcription stays off: transcribe_audio
    reads server-local file paths, which agents on this platform never have.
    """
    # OpenAITools raises without the key; the registry import must not.
    if not getenv("OPENAI_API_KEY"):
        return []
    return [OpenAITools(enable_transcription=False, image_model="gpt-image-2")]


def get_file_generation_tools() -> list[FileGenerationTools]:
    """Downloadable files (JSON, CSV, TXT, HTML, code) as in-memory run artifacts."""
    return [FileGenerationTools(enable_pdf_generation=False, enable_docx_generation=False)]


def get_knowledge_management_tools() -> KnowledgeManagementTools:
    """The write side of the product knowledge base, mounted on Platform Builder."""
    return KnowledgeManagementTools(knowledge=product_knowledge)
