# Refund Arena — backend

AgentOS runtime plus the North & Co shop. Compose is **not** in this folder. From the repository root:

```bash
cp .env.example .env    # XAI_TOKEN_ENCRYPTION_KEY
docker compose up --build
docker compose exec backend python -m app.xai_login
```

Desk: http://localhost:3000  
API: http://localhost:8000/docs  
Service name: `backend` (`refund-arena-backend`). Database: `db`. Frontend: `frontend` (`refund-arena-frontend`).

## What runs here

| Piece | Path | Role |
|---|---|---|
| Helpdesk agent | `agents/refund_helpdesk.py` | One Agent, four tools, first in `app/main.py` |
| Shop world | `shop/` | JSON ledger, policy, tickets, scorer, `/arena` routes |
| Platform agents | `agents/builder.py` etc. | AgentOS traces / Studio — not the product |
| Evals | `evals/cases.py` | Platform smoke + `arena` tag for the fourteen tickets |

Durable state for refunds is `shop/data/ledger.json`, not a user memory store. `issue_refund` always appends a payments row. That is intentional: a production desk would lock ineligible writes; this plate must be able to fail.

## Local AgentOS

| Setting | Value |
|---|---|
| UI | https://os.agno.com |
| Type | Local |
| Endpoint | `http://localhost:8000` |
| Name | `Local AgentOS` |

## Arena API

Mounted on the same FastAPI app (CORS allows `localhost:3000` / `5173` for the SPA). Prefer `POST /arena/run` in a loop from the desk; `run-all` is the CLI equivalent.

| Method | Path |
|---|---|
| GET | `/arena/health` |
| GET | `/arena/world` |
| GET | `/arena/policy` |
| GET | `/arena/tickets` |
| GET | `/arena/orders` |
| GET | `/arena/payments` |
| POST | `/arena/reset` |
| POST | `/arena/run` `{ "ticket_id": "t002", "config_id": "production" }` |
| POST | `/arena/jobs` `{ "config_id": "production", "sample": 12, "concurrency": 4 }` |
| GET | `/arena/jobs/{id}` |
| GET | `/arena/board?config_id=production` |
| GET/POST/PUT/DELETE | `/arena/configs` |

`config_id` is a prompt config (`naive` / `policy` / `production` or a custom one). The ship gate is `score.passed_gate` / board `forbidden_write`. Jobs run tickets in parallel on isolated in-memory ledgers.

## Commands

```bash
# from repo root
docker compose exec backend python -m shop.run_arena --config production --sample 12 --concurrency 4
docker compose exec backend python -m evals --tag arena
./backend/scripts/mcp_check.sh
docker compose logs -f backend
```

Add a ticket in `shop/data/tickets.json`. Change policy in `shop/policy.txt`. Reset the ledger with `POST /arena/reset` or `reset_to_seed()`.

## Coding-agent skills

Under `.agents/skills/`. Run Compose from the repo root; the API container is `refund-arena-backend`.

Based on [agno-agi/agentos-docker](https://github.com/agno-agi/agentos-docker). Template updates: copy forward, do not nest a second git remote in this folder.
