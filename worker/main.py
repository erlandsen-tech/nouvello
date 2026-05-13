"""FastAPI worker for picture-book generation (PLAN.md W3).

Hosts the Inngest serve endpoint at /api/inngest. The Next.js app (W4) enqueues
`book.generate` events via `inngest.send(...)`; this process runs them.

Local dev:
    .venv/bin/uvicorn worker.main:app --reload --port 8000
    npx inngest-cli@latest dev                                     # in another terminal
"""

from __future__ import annotations

import inngest
import inngest.fast_api
from fastapi import FastAPI

from worker.jobs import functions, inngest_client

app = FastAPI(title="drømmevev worker", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


inngest.fast_api.serve(app, inngest_client, functions)
