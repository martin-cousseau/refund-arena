# Refund Arena — backend

AgentOS runtime plus the North & Co shop. Compose is **not** in this folder. From the repository root:

```bash
cp .env.example .env    # OPENAI_API_KEY
docker compose up --build
```

API: http://localhost:8000/docs  
Service name: `backend` (`refund-arena-backend`). Database: `db`.

## What runs here

| Piece | Path | Role |
|---|---|---|
| Helpdesk agent | `agents/refund_helpdesk.py` | One Agent, four tools, first in `app/main.py` |
| Shop world | `shop/` | JSON ledger, policy, tickets, scorer, `/arena` routes |
| Platform agents | `agents/builder.py` etc. | AgentOS traces / Studio — not the product |
| Evals | `evals/cases.py` | Platform smoke + `arena` tag for the ten tickets |

Durable state for refunds is `shop/data/ledger.json`, not a user memory store. `issue_refund` always appends a payments row. That is intentional: a production desk would lock ineligible writes; this plate must be able to fail.

## Local AgentOS

| Setting | Value |
|---|---|
| UI | https://os.agno.com |
| Type | Local |
| Endpoint | `http://localhost:8000` |
| Name | `Local AgentOS` |

## Arena API

Mounted on the same FastAPI app (CORS allows `localhost:3000` / `5173` for the future SPA).

| Method | Path |
|---|---|
| GET | `/arena/health` |
| GET | `/arena/policy` |
| GET | `/arena/tickets` |
| GET | `/arena/orders` |
| GET | `/arena/payments` |
| POST | `/arena/reset` |
| POST | `/arena/run` `{ "ticket_id": "t02", "reset": true }` |
| POST | `/arena/run-all` |
| GET | `/arena/scoreboard` |

## Commands

```bash
# from repo root
docker compose exec backend python -m shop.run_arena
docker compose exec backend python -m evals --tag arena
./backend/scripts/mcp_check.sh
docker compose logs -f backend
```

Add a ticket in `shop/data/tickets.json`. Change policy in `shop/policy.txt`. Reset the ledger with `POST /arena/reset` or `reset_to_seed()`.

## Coding-agent skills

Under `.agents/skills/`. Run Compose from the repo root; the API container is `refund-arena-backend`.

Based on [agno-agi/agentos-docker](https://github.com/agno-agi/agentos-docker). Template updates: copy forward, do not nest a second git remote in this folder.
