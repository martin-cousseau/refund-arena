"""Persisted arena runs.

SQLite is the store. Each execution of a dataset ticket is its own row, so a
rerun does not replace the previous one. Rows are distinct by model, prompt
version, and attempt. The board still shows the latest attempt per ticket.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.settings import MODEL_ID
from shop.claim_parse import prefetch_claims
from shop.configs import get_config
from shop.score import Board, TicketScore, score_run, score_ticket
from shop.resolvd_book import CASES_PATH
from shop.store import SHOP_DIR, load_tickets

RESULTS_DIR = SHOP_DIR / "results"
RUNS_PATH = RESULTS_DIR / "runs.jsonl"
DATASET_ID = "martincousseau/refund-arena"
UNRECORDED = "unrecorded"

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_versions (
  id INTEGER PRIMARY KEY,
  config_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  instructions_hash TEXT NOT NULL,
  instructions TEXT NOT NULL,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (config_id, version),
  UNIQUE (config_id, instructions_hash)
);

CREATE TABLE IF NOT EXISTS dataset_items (
  id INTEGER PRIMARY KEY,
  dataset_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  ticket_json TEXT NOT NULL,
  UNIQUE (dataset_id, item_id, content_hash)
);

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  config_id TEXT NOT NULL,
  model_id TEXT NOT NULL,
  prompt_version_id INTEGER NOT NULL REFERENCES prompt_versions(id),
  dataset_id TEXT NOT NULL,
  dataset_revision TEXT NOT NULL,
  created_at TEXT NOT NULL,
  kind TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_items (
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id),
  dataset_item_id INTEGER NOT NULL REFERENCES dataset_items(id),
  item_id TEXT NOT NULL,
  config_id TEXT NOT NULL,
  model_id TEXT NOT NULL,
  prompt_version_id INTEGER NOT NULL REFERENCES prompt_versions(id),
  attempt INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  passed_gate INTEGER NOT NULL,
  passed_desk INTEGER NOT NULL,
  forbidden_write INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_run_items_config_item_time
  ON run_items (config_id, item_id, created_at);
CREATE INDEX IF NOT EXISTS idx_run_items_identity
  ON run_items (item_id, model_id, prompt_version_id);
"""


def db_path() -> Path:
    override = os.getenv("ARENA_RUNS_DB")
    if override:
        return Path(override)
    return RESULTS_DIR / "runs.sqlite"


def jsonl_path() -> Path:
    override = os.getenv("ARENA_RUNS_JSONL")
    if override:
        return Path(override)
    return RUNS_PATH


def _now() -> str:
    return datetime.now(UTC).isoformat()


def instructions_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ticket_content_hash(ticket: dict[str, Any]) -> str:
    canonical = json.dumps(ticket, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def dataset_stamp(ticket: dict[str, Any] | None) -> dict[str, str]:
    row = ticket or {}
    return {
        "dataset_id": DATASET_ID,
        "item_id": str(row.get("id") or ""),
        "content_hash": ticket_content_hash(row),
    }


def dataset_revision() -> str:
    if not CASES_PATH.exists():
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(CASES_PATH.read_bytes()).hexdigest()


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(_SCHEMA)
    _maybe_import(conn)
    return conn


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = _connect()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()


def _prompt_public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "version": int(row["version"]),
        "instructions_hash": str(row["instructions_hash"]),
    }


def _ensure_prompt_version(
    conn: sqlite3.Connection,
    *,
    config_id: str,
    instructions: str,
    name: str,
    created_at: str,
) -> dict[str, Any]:
    digest = instructions_hash(instructions)
    existing = conn.execute(
        "SELECT * FROM prompt_versions WHERE config_id = ? AND instructions_hash = ?",
        (config_id, digest),
    ).fetchone()
    if existing is not None:
        return _prompt_public(existing)
    # Version 0 is only the JSONL import placeholder. Live runs start at 1.
    version = conn.execute(
        "SELECT COALESCE(MAX(version), 0) + 1 AS n FROM prompt_versions WHERE config_id = ? AND version > 0",
        (config_id,),
    ).fetchone()
    cur = conn.execute(
        """
        INSERT INTO prompt_versions (config_id, version, instructions_hash, instructions, name, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (config_id, int(version["n"]), digest, instructions, name, created_at),
    )
    row = conn.execute("SELECT * FROM prompt_versions WHERE id = ?", (cur.lastrowid,)).fetchone()
    if row is None:
        raise RuntimeError("prompt version insert failed")
    return _prompt_public(row)


def _unrecorded_prompt(conn: sqlite3.Connection, config_id: str, created_at: str) -> dict[str, Any]:
    existing = conn.execute(
        "SELECT * FROM prompt_versions WHERE config_id = ? AND version = 0",
        (config_id,),
    ).fetchone()
    if existing is not None:
        return _prompt_public(existing)
    cur = conn.execute(
        """
        INSERT INTO prompt_versions (config_id, version, instructions_hash, instructions, name, created_at)
        VALUES (?, 0, ?, '', ?, ?)
        """,
        (config_id, UNRECORDED, config_id, created_at),
    )
    row = conn.execute("SELECT * FROM prompt_versions WHERE id = ?", (cur.lastrowid,)).fetchone()
    if row is None:
        raise RuntimeError("unrecorded prompt insert failed")
    return _prompt_public(row)


def _ensure_dataset_item(conn: sqlite3.Connection, ticket: dict[str, Any]) -> tuple[int, str]:
    item_id = str(ticket.get("id") or "")
    digest = ticket_content_hash(ticket)
    existing = conn.execute(
        "SELECT id FROM dataset_items WHERE dataset_id = ? AND item_id = ? AND content_hash = ?",
        (DATASET_ID, item_id, digest),
    ).fetchone()
    if existing is not None:
        return int(existing["id"]), digest
    blob = json.dumps(ticket, sort_keys=True, ensure_ascii=False)
    cur = conn.execute(
        """
        INSERT INTO dataset_items (dataset_id, item_id, content_hash, ticket_json)
        VALUES (?, ?, ?, ?)
        """,
        (DATASET_ID, item_id, digest, blob),
    )
    if cur.lastrowid is None:
        raise RuntimeError("dataset item insert failed")
    return int(cur.lastrowid), digest


def _next_attempt(conn: sqlite3.Connection, item_id: str, model_id: str, prompt_version_id: int) -> int:
    row = conn.execute(
        """
        SELECT COALESCE(MAX(attempt), 0) + 1 AS n
        FROM run_items
        WHERE item_id = ? AND model_id = ? AND prompt_version_id = ?
        """,
        (item_id, model_id, prompt_version_id),
    ).fetchone()
    return int(row["n"])


def _score_bits(score: dict[str, Any]) -> tuple[int, int, int]:
    forbidden = bool(score.get("forbidden_write"))
    desk_flags = (
        forbidden,
        bool(score.get("missing_read")),
        bool(score.get("lying_close")),
        bool(score.get("missed_refund")),
        bool(score.get("missed_escalate")),
        bool(score.get("wrong_amount")),
        bool(score.get("near_miss")),
        bool(score.get("caved")),
    )
    if "passed_gate" in score:
        passed_gate = bool(score.get("passed_gate"))
    else:
        passed_gate = not forbidden
    if "passed_desk" in score:
        passed_desk = bool(score.get("passed_desk"))
    else:
        passed_desk = not any(desk_flags)
    return int(passed_gate), int(passed_desk), int(forbidden)


def _insert_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    config_id: str,
    model_id: str,
    prompt_version_id: int,
    revision: str,
    created_at: str,
    kind: str,
) -> None:
    conn.execute(
        """
        INSERT INTO runs (
            id, config_id, model_id, prompt_version_id, dataset_id, dataset_revision, created_at, kind
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, config_id, model_id, prompt_version_id, DATASET_ID, revision, created_at, kind),
    )


def _insert_item(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    dataset_item_id: int,
    payload: dict[str, Any],
    prompt_version_id: int,
) -> None:
    score = payload.get("score") if isinstance(payload.get("score"), dict) else {}
    passed_gate, passed_desk, forbidden = _score_bits(score)
    conn.execute(
        """
        INSERT INTO run_items (
            run_id, dataset_item_id, item_id, config_id, model_id, prompt_version_id,
            attempt, created_at, payload_json, passed_gate, passed_desk, forbidden_write
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            dataset_item_id,
            str(payload.get("dataset", {}).get("item_id") or ""),
            str(payload.get("config_id") or ""),
            str(payload.get("model") or ""),
            prompt_version_id,
            int(payload.get("attempt") or 0),
            str(payload.get("created_at") or ""),
            json.dumps(payload, ensure_ascii=False),
            passed_gate,
            passed_desk,
            forbidden,
        ),
    )


def _instructions_for_batch(
    config_id: str,
    instructions: str | None,
    name: str | None,
) -> tuple[str, str]:
    if instructions is not None:
        return instructions, name or config_id
    config = get_config(config_id)
    if config is None:
        return "", name or config_id
    return str(config.get("instructions") or ""), str(name or config.get("name") or config_id)


def begin_run(*, config_id: str, model_id: str, kind: str = "single") -> dict[str, Any]:
    """Open one batch and snapshot the prompt and dataset file revision."""
    key = (config_id or "").strip()
    model = (model_id or "").strip()
    if not model:
        raise ValueError("model_id is required")
    created_at = _now()
    run_id = uuid.uuid4().hex
    revision = dataset_revision()
    with _db() as conn:
        config = get_config(key)
        if config is None:
            raise KeyError(key)
        instructions = str(config.get("instructions") or "")
        label = str(config.get("name") or key)
        prompt = _ensure_prompt_version(
            conn,
            config_id=key,
            instructions=instructions,
            name=label,
            created_at=created_at,
        )
        _insert_run(
            conn,
            run_id=run_id,
            config_id=key,
            model_id=model,
            prompt_version_id=int(prompt["id"]),
            revision=revision,
            created_at=created_at,
            kind=kind,
        )
    return {
        "id": run_id,
        "config_id": key,
        "model_id": model,
        "instructions": instructions,
        "prompt_version": prompt,
        "dataset_id": DATASET_ID,
        "dataset_revision": revision,
        "created_at": created_at,
        "kind": kind,
    }


def append_run(
    payload: dict[str, Any],
    *,
    run_id: str | None = None,
    instructions: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Insert one ticket execution. Fills model, prompt version, dataset, and attempt on payload."""
    config_id = str(payload.get("config_id") or "")
    ticket = payload.get("ticket") if isinstance(payload.get("ticket"), dict) else {}
    created_at = _now()
    with _db() as conn:
        if run_id is None:
            model_id = str(payload.get("model") or "").strip() or MODEL_ID
            text, label = _instructions_for_batch(config_id, instructions, name)
            prompt = _ensure_prompt_version(
                conn,
                config_id=config_id,
                instructions=text,
                name=label,
                created_at=created_at,
            )
            run_id = uuid.uuid4().hex
            _insert_run(
                conn,
                run_id=run_id,
                config_id=config_id,
                model_id=model_id,
                prompt_version_id=int(prompt["id"]),
                revision=dataset_revision(),
                created_at=created_at,
                kind="single",
            )
        else:
            batch = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if batch is None:
                raise KeyError(run_id)
            prompt_row = conn.execute(
                "SELECT * FROM prompt_versions WHERE id = ?",
                (batch["prompt_version_id"],),
            ).fetchone()
            if prompt_row is None:
                raise KeyError(run_id)
            prompt = _prompt_public(prompt_row)
            model_id = str(payload.get("model") or "").strip() or str(batch["model_id"])
        dataset_item_id, digest = _ensure_dataset_item(conn, ticket)
        item_id = str(ticket.get("id") or "")
        attempt = _next_attempt(conn, item_id, model_id, int(prompt["id"]))
        payload["config_id"] = config_id
        payload["model"] = model_id
        payload["prompt_version"] = prompt
        payload["dataset"] = {"dataset_id": DATASET_ID, "item_id": item_id, "content_hash": digest}
        payload["attempt"] = attempt
        payload["run_id"] = run_id
        payload["created_at"] = created_at
        _insert_item(
            conn,
            run_id=run_id,
            dataset_item_id=dataset_item_id,
            payload=payload,
            prompt_version_id=int(prompt["id"]),
        )
    return payload


def _select_payloads(
    conn: sqlite3.Connection,
    *,
    config_id: str | None = None,
    model_id: str | None = None,
    prompt_version: int | None = None,
    item_id: str | None = None,
    newest_first: bool = False,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    args: list[Any] = []
    if config_id is not None:
        clauses.append("ri.config_id = ?")
        args.append(config_id)
    if model_id:
        clauses.append("ri.model_id = ?")
        args.append(model_id)
    if prompt_version is not None:
        clauses.append("pv.version = ?")
        args.append(prompt_version)
    if item_id is not None:
        clauses.append("ri.item_id = ?")
        args.append(item_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    direction = "DESC" if newest_first else "ASC"
    sql = f"""
        SELECT ri.payload_json
        FROM run_items ri
        JOIN prompt_versions pv ON pv.id = ri.prompt_version_id
        {where}
        ORDER BY ri.created_at {direction}, ri.id {direction}
    """
    rows: list[dict[str, Any]] = []
    for row in conn.execute(sql, args):
        item = json.loads(row["payload_json"])
        if isinstance(item, dict):
            rows.append(item)
    return rows


def load_runs(
    config_id: str | None = None,
    *,
    model_id: str | None = None,
    prompt_version: int | None = None,
) -> list[dict[str, Any]]:
    with _db() as conn:
        return _select_payloads(conn, config_id=config_id, model_id=model_id, prompt_version=prompt_version)


def recorded_attempt(row: dict[str, Any]) -> bool:
    """True when this execution names a model and a saved prompt version.

    JSONL imports keep model and prompt as unrecorded. They stay in history
    and do not count as a run of a prompt env.
    """
    model = str(row.get("model") or "").strip()
    if not model or model == UNRECORDED:
        return False
    prompt = row.get("prompt_version") if isinstance(row.get("prompt_version"), dict) else {}
    try:
        version = int(prompt.get("version"))
    except (TypeError, ValueError):
        return False
    return version > 0


def latest_by_ticket(
    config_id: str,
    *,
    model_id: str | None = None,
    prompt_version: int | None = None,
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in load_runs(config_id, model_id=model_id, prompt_version=prompt_version):
        if not recorded_attempt(row):
            continue
        ticket = row.get("ticket") or {}
        tid = str(ticket.get("id") or "")
        if tid:
            latest[tid] = row
    return latest


def history_for(config_id: str, ticket_id: str) -> list[dict[str, Any]]:
    """Every saved attempt for one ticket, newest first."""
    with _db() as conn:
        return _select_payloads(conn, config_id=config_id, item_id=ticket_id, newest_first=True)


def _score_from_payload(payload: dict[str, Any]) -> TicketScore:
    ticket = payload.get("ticket") or {}
    score = payload.get("score") or {}
    return TicketScore(
        ticket_id=str(ticket.get("id") or "unknown"),
        title=str(ticket.get("title") or ticket.get("id") or ""),
        forbidden_write=bool(score.get("forbidden_write")),
        missing_read=bool(score.get("missing_read")),
        lying_close=bool(score.get("lying_close")),
        closed=bool(score.get("closed")),
        missed_refund=bool(score.get("missed_refund")),
        missed_escalate=bool(score.get("missed_escalate")),
        wrong_amount=bool(score.get("wrong_amount")),
        near_miss=bool(score.get("near_miss")),
        caved=bool(score.get("caved")),
        tools=list(payload.get("tools") or []),
        reason=str(score.get("reason") or ""),
    )


def board_for(
    config_id: str,
    *,
    total: int | None = None,
    model_id: str | None = None,
    prompt_version: int | None = None,
) -> dict[str, Any]:
    latest = latest_by_ticket(config_id, model_id=model_id, prompt_version=prompt_version)
    scores = [_score_from_payload(row) for row in latest.values()]
    board: Board = score_run(scores) if scores else score_run([])
    payload = board.as_dict()
    n_tickets = total if total is not None else len(load_tickets())
    if not scores:
        payload["closed_tickets"] = 0
        payload["forbidden_write"] = 0
        payload["gate_fail"] = 0
    payload["config_id"] = config_id
    payload["ran"] = len(scores)
    payload["total"] = n_tickets
    if model_id:
        payload["model"] = model_id
    if prompt_version is not None:
        payload["prompt_version"] = prompt_version
    payload["runs"] = [_board_run(row) for row in latest.values()]
    return payload


def _board_run(row: dict[str, Any]) -> dict[str, Any]:
    prompt = row.get("prompt_version") if isinstance(row.get("prompt_version"), dict) else {}
    return {
        "ticket_id": row["ticket"]["id"],
        "title": row["ticket"].get("title"),
        "score": row["score"],
        "content": row.get("content"),
        "tools": row.get("tools") or [],
        "model": row.get("model"),
        "prompt_version": prompt.get("version"),
        "attempt": row.get("attempt"),
        "created_at": row.get("created_at"),
    }


def _without_rows(after: list[dict[str, Any]], delta: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = {(row.get("order_id"), row.get("at"), row.get("source"), row.get("reason")) for row in delta}
    return [
        row for row in after if (row.get("order_id"), row.get("at"), row.get("source"), row.get("reason")) not in keys
    ]


def rescore_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Recompute score from the stored trajectory. Does not call the model."""
    ticket = payload.get("ticket") or {}
    after_pay = list(payload.get("payments") or [])
    delta_pay = list(payload.get("payments_delta") or [])
    after_esc = list(payload.get("escalations") or [])
    delta_esc = list(payload.get("escalations_delta") or [])
    run = {
        "content": payload.get("content") or "",
        "tools": payload.get("tool_calls") or [{"name": name} for name in (payload.get("tools") or [])],
        "turns": list(payload.get("turns") or []),
    }
    scored = score_ticket(
        ticket,
        run,
        payments_before=_without_rows(after_pay, delta_pay),
        payments_after=after_pay,
        escalations_before=_without_rows(after_esc, delta_esc),
        escalations_after=after_esc,
    )
    next_payload = dict(payload)
    next_payload["score"] = {
        "forbidden_write": scored.forbidden_write,
        "missing_read": scored.missing_read,
        "lying_close": scored.lying_close,
        "closed": scored.closed,
        "missed_refund": scored.missed_refund,
        "missed_escalate": scored.missed_escalate,
        "wrong_amount": scored.wrong_amount,
        "near_miss": scored.near_miss,
        "caved": scored.caved,
        "reason": scored.reason,
        "passed_gate": scored.passed_gate(),
        "passed_desk": scored.passed_desk(),
    }
    return next_payload


def rescore_runs() -> dict[str, int]:
    """Rewrite stored scores from replies and ledger deltas."""
    with _db() as conn:
        rows = list(conn.execute("SELECT id, payload_json FROM run_items ORDER BY id"))
        parsed: list[tuple[int, dict[str, Any]]] = []
        replies: list[str] = []
        for row in rows:
            try:
                item = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            parsed.append((int(row["id"]), item))
            replies.append(str(item.get("content") or ""))
            for turn in item.get("turns") or []:
                if isinstance(turn, dict):
                    replies.append(str(turn.get("content") or ""))
        prefetch_claims(replies)
        changed = 0
        for row_id, item in parsed:
            next_item = rescore_payload(item)
            if next_item.get("score") != item.get("score"):
                changed += 1
            passed_gate, passed_desk, forbidden = _score_bits(next_item.get("score") or {})
            conn.execute(
                """
                UPDATE run_items
                SET payload_json = ?, passed_gate = ?, passed_desk = ?, forbidden_write = ?
                WHERE id = ?
                """,
                (json.dumps(next_item, ensure_ascii=False), passed_gate, passed_desk, forbidden, row_id),
            )
    return {"rows": len(parsed), "changed": changed}


def reset_runs(config_id: str) -> None:
    """Drop saved runs for one config. Prompt versions and dataset items stay."""
    with _db() as conn:
        conn.execute("DELETE FROM run_items WHERE config_id = ?", (config_id,))
        conn.execute("DELETE FROM runs WHERE config_id = ?", (config_id,))


def _maybe_import(conn: sqlite3.Connection) -> None:
    seen = conn.execute("SELECT value FROM meta WHERE key = 'imported_jsonl'").fetchone()
    if seen is not None:
        return
    count = conn.execute("SELECT COUNT(*) AS n FROM run_items").fetchone()
    if int(count["n"]):
        conn.execute("INSERT INTO meta (key, value) VALUES ('imported_jsonl', 'skipped')")
        return
    path = jsonl_path()
    if not path.exists():
        conn.execute("INSERT INTO meta (key, value) VALUES ('imported_jsonl', 'absent')")
        return
    _import_jsonl(conn, path)
    conn.execute("INSERT INTO meta (key, value) VALUES ('imported_jsonl', 'done')")


def _import_jsonl(conn: sqlite3.Connection, path: Path) -> None:
    """One row per JSONL line. Missing model and prompt stay unrecorded.

    The file has no per-line clock, so attempts keep file order and share its mtime.
    """
    base = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    index = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        _import_line(conn, item, index, base)
        index += 1


def _import_line(conn: sqlite3.Connection, item: dict[str, Any], index: int, base: datetime) -> None:
    config_id = str(item.get("config_id") or "unknown")
    ticket = item.get("ticket") if isinstance(item.get("ticket"), dict) else {}
    model_id = str(item.get("model") or "").strip() or UNRECORDED
    created_at = (base + timedelta(milliseconds=index)).isoformat()
    prompt = _unrecorded_prompt(conn, config_id, created_at)
    dataset_item_id, digest = _ensure_dataset_item(conn, ticket)
    item_id = str(ticket.get("id") or "")
    attempt = _next_attempt(conn, item_id, model_id, int(prompt["id"]))
    run_id = uuid.uuid4().hex
    _insert_run(
        conn,
        run_id=run_id,
        config_id=config_id,
        model_id=model_id,
        prompt_version_id=int(prompt["id"]),
        revision=UNRECORDED,
        created_at=created_at,
        kind="single",
    )
    item["model"] = model_id
    item["prompt_version"] = prompt
    item["dataset"] = {"dataset_id": DATASET_ID, "item_id": item_id, "content_hash": digest}
    item["attempt"] = attempt
    item["run_id"] = run_id
    item["created_at"] = created_at
    _insert_item(
        conn,
        run_id=run_id,
        dataset_item_id=dataset_item_id,
        payload=item,
        prompt_version_id=int(prompt["id"]),
    )


if __name__ == "__main__":
    import sys

    stats = rescore_runs()
    print(f"rescored {stats['rows']} runs, {stats['changed']} scores changed")
    sys.exit(0)
