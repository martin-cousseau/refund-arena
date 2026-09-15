"""Async job queue for arena runs. One job at a time; tickets inside a job run in parallel."""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from shop.configs import get_config
from shop.runs import append_run, board_for
from shop.store import load_tickets

JobStatus = Literal["queued", "running", "cancelling", "done", "cancelled", "failed"]
ItemStatus = Literal["queued", "running", "done", "error", "cancelled"]

DEFAULT_CONCURRENCY = 4
MAX_CONCURRENCY = 8

_jobs: dict[str, dict[str, Any]] = {}
_queue: asyncio.Queue[str] = asyncio.Queue()
_dispatcher: asyncio.Task[None] | None = None
_lock = asyncio.Lock()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _public_job(job: dict[str, Any]) -> dict[str, Any]:
    items = job["items"]
    done = sum(1 for item in items if item["status"] in {"done", "error", "cancelled"})
    return {
        "id": job["id"],
        "config_id": job["config_id"],
        "status": job["status"],
        "concurrency": job["concurrency"],
        "created_at": job["created_at"],
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "total": len(items),
        "done": done,
        "error": job.get("error"),
        "board": job.get("board"),
        "items": [
            {
                "ticket_id": item["ticket_id"],
                "title": item.get("title"),
                "status": item["status"],
                "error": item.get("error"),
                "score": (item.get("run") or {}).get("score") if item.get("run") else None,
                "reason": ((item.get("run") or {}).get("score") or {}).get("reason"),
            }
            for item in items
        ],
    }


def get_job(job_id: str) -> dict[str, Any] | None:
    job = _jobs.get(job_id)
    if job is None:
        return None
    return _public_job(job)


def list_jobs(limit: int = 20) -> list[dict[str, Any]]:
    rows = sorted(_jobs.values(), key=lambda row: row["created_at"], reverse=True)
    return [_public_job(row) for row in rows[:limit]]


def active_job() -> dict[str, Any] | None:
    for status in ("running", "cancelling", "queued"):
        for row in sorted(_jobs.values(), key=lambda item: item["created_at"]):
            if row["status"] == status:
                return _public_job(row)
    return None


def resolve_ticket_ids(
    *,
    ticket_ids: list[str] | None = None,
    sample: int | None = None,
    all_tickets: bool = False,
) -> list[str]:
    tickets = load_tickets()
    by_id = {str(row["id"]): row for row in tickets}
    if ticket_ids:
        missing = [tid for tid in ticket_ids if tid not in by_id]
        if missing:
            raise KeyError(f"unknown tickets: {', '.join(missing[:8])}")
        return list(dict.fromkeys(ticket_ids))
    if all_tickets:
        return [str(row["id"]) for row in tickets]
    if sample is not None:
        n = max(1, min(int(sample), len(tickets)))
        picked = random.sample(tickets, n)
        return [str(row["id"]) for row in picked]
    raise ValueError("provide ticket_ids, sample, or all")


async def ensure_dispatcher() -> None:
    global _dispatcher
    async with _lock:
        if _dispatcher is None or _dispatcher.done():
            _dispatcher = asyncio.create_task(_dispatch_loop(), name="arena-dispatcher")


async def submit_job(
    *,
    config_id: str,
    ticket_ids: list[str],
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict[str, Any]:
    if get_config(config_id) is None:
        raise KeyError(f"unknown config {config_id}")
    tickets = {str(row["id"]): row for row in load_tickets()}
    conc = max(1, min(int(concurrency or DEFAULT_CONCURRENCY), MAX_CONCURRENCY))
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "config_id": config_id,
        "status": "queued",
        "concurrency": conc,
        "cancel": False,
        "created_at": _now(),
        "started_at": None,
        "finished_at": None,
        "error": None,
        "board": None,
        "items": [
            {
                "ticket_id": tid,
                "title": (tickets[tid].get("title") if tid in tickets else tid),
                "status": "queued",
                "error": None,
                "run": None,
            }
            for tid in ticket_ids
        ],
    }
    _jobs[job_id] = job
    await ensure_dispatcher()
    await _queue.put(job_id)
    return _public_job(job)


def request_cancel(job_id: str) -> dict[str, Any]:
    job = _jobs.get(job_id)
    if job is None:
        raise KeyError(job_id)
    if job["status"] in {"done", "cancelled", "failed"}:
        return _public_job(job)
    job["cancel"] = True
    if job["status"] == "queued":
        job["status"] = "cancelled"
        job["finished_at"] = _now()
        for item in job["items"]:
            if item["status"] == "queued":
                item["status"] = "cancelled"
    else:
        job["status"] = "cancelling"
    return _public_job(job)


async def _dispatch_loop() -> None:
    while True:
        job_id = await _queue.get()
        job = _jobs.get(job_id)
        if job is None or job["status"] == "cancelled":
            continue
        try:
            await _run_job(job)
        except Exception as exc:  # noqa: BLE001 — job must not kill the dispatcher
            job["status"] = "failed"
            job["error"] = str(exc)
            job["finished_at"] = _now()


async def _run_job(job: dict[str, Any]) -> None:
    from shop.run_arena import execute_ticket

    job["status"] = "running"
    job["started_at"] = _now()
    tickets = {str(row["id"]): row for row in load_tickets()}
    semaphore = asyncio.Semaphore(job["concurrency"])

    async def run_item(item: dict[str, Any]) -> None:
        if job["cancel"]:
            item["status"] = "cancelled"
            return
        ticket = tickets.get(item["ticket_id"])
        if ticket is None:
            item["status"] = "error"
            item["error"] = "unknown ticket"
            return
        async with semaphore:
            if job["cancel"]:
                item["status"] = "cancelled"
                return
            item["status"] = "running"
            try:
                _scored, payload = await execute_ticket(ticket, config_id=job["config_id"])
                item["run"] = payload
                item["status"] = "done"
                append_run(payload)
            except Exception as exc:  # noqa: BLE001 — per-ticket isolation
                item["status"] = "error"
                item["error"] = str(exc)

    await asyncio.gather(*(run_item(item) for item in job["items"]))
    job["board"] = board_for(job["config_id"])
    job["finished_at"] = _now()
    if job["cancel"]:
        job["status"] = "cancelled"
    elif any(item["status"] == "error" for item in job["items"]):
        job["status"] = "failed"
    else:
        job["status"] = "done"
