# Refund Arena — frontend

North Desk: operator radar for North & Co. React + Vite + shadcn. Talks to `/arena` on the backend.

Pages: Overview (gate, graphs, fails), Queue (ticket review), Runs (per-config table), Shop (orders / policy / ledger), Prompts (editable configs).

```bash
# from repo root
cp .env.example .env    # XAI_TOKEN_ENCRYPTION_KEY
docker compose up --build
docker compose exec backend python -m app.xai_login
```

Desk: http://localhost:3000  
API: http://localhost:8000

Local without the frontend container:

```bash
cd frontend
pnpm install
pnpm dev                 # http://localhost:3000, proxies /arena to :8000
```

Cap 50, cap 10, and cap 200 are limit configs on the same gold. Cap 50 is the ship row. The board for a config grows as you run cases and survives a reload.
