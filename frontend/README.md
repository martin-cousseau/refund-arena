# Refund Arena — frontend

React app, not built yet. It will live in this directory and talk to the backend already running in Compose.

- `GET /arena/tickets`, `POST /arena/run`, `GET /arena/scoreboard`, `GET /arena/payments`
- `POST /agents/refund-helpdesk/runs` for a live chat column
- CORS is already open for `http://localhost:3000` and `http://localhost:5173`

When this folder has a `Dockerfile`:

```bash
# from repo root
docker compose --profile frontend up --build
```

The `frontend` service is declared in the root `compose.yaml` with `profiles: [frontend]`, so `docker compose up` keeps working without this app.
