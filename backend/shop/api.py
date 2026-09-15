"""Thin HTTP plug for the operator desk. No HTML."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.settings import MODEL_ID, SIGNIN_HINT, inference_ready, supergrok_signed_in
from shop.configs import (
    create_config,
    delete_config,
    ensure_configs,
    get_config,
    list_configs,
    reset_config,
    update_config,
)
from shop.queue import (
    DEFAULT_CONCURRENCY,
    active_job,
    get_job,
    list_jobs,
    request_cancel,
    resolve_ticket_ids,
    submit_job,
)
from shop.run_arena import run_ticket
from shop.runs import board_for, latest_by_ticket, reset_runs
from shop.store import get_ledger, load_policy, load_tickets, reset_to_seed, world

router = APIRouter(prefix="/arena", tags=["arena"])


class RunBody(BaseModel):
    ticket_id: str
    config_id: str = "production"
    persist: bool = True


class JobBody(BaseModel):
    config_id: str = "production"
    ticket_ids: list[str] | None = None
    sample: int | None = Field(default=None, ge=1, le=500)
    all: bool = False
    concurrency: int = Field(default=DEFAULT_CONCURRENCY, ge=1, le=8)


class ConfigCreateBody(BaseModel):
    name: str = "Untitled"
    instructions: str = ""
    clone_from: str | None = None


class ConfigUpdateBody(BaseModel):
    name: str | None = None
    instructions: str | None = None


class ResetRunsBody(BaseModel):
    config_id: str


def _require_inference() -> None:
    if inference_ready():
        return
    raise HTTPException(status_code=503, detail=SIGNIN_HINT)


def _ticket(ticket_id: str) -> dict[str, Any]:
    for row in load_tickets():
        if row["id"] == ticket_id or row.get("title") == ticket_id:
            return row
    raise HTTPException(status_code=404, detail=f"unknown ticket {ticket_id}")


@router.get("/health")
def arena_health() -> dict[str, Any]:
    ledger = get_ledger()
    return {
        "ok": True,
        "model": MODEL_ID,
        "xai_signed_in": supergrok_signed_in(),
        "orders": len(ledger["orders"]),
        "payments": len(ledger["payments"]),
        "tickets": len(load_tickets()),
        "configs": [row["id"] for row in list_configs()],
    }


@router.get("/world")
def arena_world() -> dict[str, Any]:
    ensure_configs()
    payload = world()
    payload["configs"] = list_configs()
    payload["model"] = MODEL_ID
    payload["xai_signed_in"] = supergrok_signed_in()
    return payload


@router.get("/policy")
def arena_policy() -> dict[str, str]:
    return {"policy": load_policy()}


@router.get("/tickets")
def arena_tickets() -> dict[str, Any]:
    return {"tickets": load_tickets()}


@router.get("/orders")
def arena_orders() -> dict[str, Any]:
    ledger = get_ledger()
    return {"orders": ledger["orders"]}


@router.get("/payments")
def arena_payments() -> dict[str, Any]:
    ledger = get_ledger()
    return {"payments": ledger["payments"], "escalations": ledger["escalations"]}


@router.post("/reset")
def arena_reset() -> dict[str, Any]:
    ledger = reset_to_seed()
    return {
        "ok": True,
        "orders": len(ledger["orders"]),
        "payments": len(ledger["payments"]),
    }


@router.get("/configs")
def arena_configs() -> dict[str, Any]:
    ensure_configs()
    return {"configs": list_configs()}


@router.post("/configs")
def arena_create_config(body: ConfigCreateBody) -> dict[str, Any]:
    ensure_configs()
    row = create_config(name=body.name, instructions=body.instructions, clone_from=body.clone_from)
    return row


@router.put("/configs/{config_id}")
def arena_update_config(config_id: str, body: ConfigUpdateBody) -> dict[str, Any]:
    try:
        return update_config(config_id, name=body.name, instructions=body.instructions)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown config {config_id}") from None


@router.delete("/configs/{config_id}")
def arena_delete_config(config_id: str) -> dict[str, Any]:
    try:
        delete_config(config_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown config {config_id}") from None
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"ok": True, "id": config_id}


@router.post("/configs/{config_id}/reset")
def arena_reset_config(config_id: str) -> dict[str, Any]:
    try:
        return reset_config(config_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown config {config_id}") from None
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/board")
def arena_board(config_id: str = Query(default="production")) -> dict[str, Any]:
    if get_config(config_id) is None:
        raise HTTPException(status_code=404, detail=f"unknown config {config_id}")
    return board_for(config_id)


@router.get("/runs")
def arena_runs(config_id: str = Query(default="production")) -> dict[str, Any]:
    latest = latest_by_ticket(config_id)
    return {"config_id": config_id, "runs": list(latest.values())}


@router.post("/runs/reset")
def arena_reset_runs(body: ResetRunsBody) -> dict[str, Any]:
    if get_config(body.config_id) is None:
        raise HTTPException(status_code=404, detail=f"unknown config {body.config_id}")
    reset_runs(body.config_id)
    return {"ok": True, "board": board_for(body.config_id)}


@router.post("/run")
async def arena_run(body: RunBody) -> dict[str, Any]:
    _require_inference()
    if get_config(body.config_id) is None:
        raise HTTPException(status_code=404, detail=f"unknown config {body.config_id}")
    ticket = _ticket(body.ticket_id)
    payload = await run_ticket(ticket, config_id=body.config_id, persist=body.persist)
    payload["board"] = board_for(body.config_id)
    return payload


@router.post("/jobs")
async def arena_submit_job(body: JobBody) -> dict[str, Any]:
    _require_inference()
    try:
        ids = resolve_ticket_ids(ticket_ids=body.ticket_ids, sample=body.sample, all_tickets=body.all)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    try:
        return await submit_job(config_id=body.config_id, ticket_ids=ids, concurrency=body.concurrency)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get("/jobs")
def arena_jobs() -> dict[str, Any]:
    return {"jobs": list_jobs(), "active": active_job()}


@router.get("/jobs/{job_id}")
def arena_job(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"unknown job {job_id}")
    return job


@router.post("/jobs/{job_id}/cancel")
def arena_cancel_job(job_id: str) -> dict[str, Any]:
    try:
        return request_cancel(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown job {job_id}") from None


@router.get("/scoreboard")
def arena_scoreboard(config_id: str = Query(default="production")) -> dict[str, Any]:
    return board_for(config_id)


@router.post("/run-all")
async def arena_run_all(body: JobBody = JobBody(all=True)) -> dict[str, Any]:
    """Queue a full or sampled run. Prefer POST /arena/jobs."""
    body.all = body.all or (not body.ticket_ids and body.sample is None)
    return await arena_submit_job(body)
