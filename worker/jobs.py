"""Inngest function definitions (PLAN.md W3).

The skeleton wires step boundaries so retries are cheap. Real stage logic lands
incrementally as the W4 input flows (write / guided / photo / drawing) come online.
For now `book.generate` only manages status transitions and loads the row.
"""

from __future__ import annotations

import os

import inngest

from pipeline import storage as _storage


inngest_client = inngest.Inngest(
    app_id="drommevev-worker",
    is_production=os.getenv("INNGEST_ENV", "dev") == "production",
)


def _supabase() -> _storage.SupabaseStore:
    store = _storage.SupabaseStore.from_env()
    if store is None:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY must be set for the worker"
        )
    return store


@inngest_client.create_function(
    fn_id="book-generate",
    trigger=inngest.TriggerEvent(event="book.generate"),
    retries=2,
)
def book_generate(ctx: inngest.Context) -> dict:
    """Run the picture-book pipeline for one book.

    Event payload: `{"book_id": "<uuid>"}`. The book row must already exist
    (created by the Next.js API when the parent submits the form).
    """
    book_id: str = ctx.event.data["book_id"]

    def _load_book() -> dict:
        store = _supabase()
        resp = store._client.table("books").select("*").eq("id", book_id).execute()
        if not resp.data:
            raise ValueError(f"book {book_id} not found")
        return resp.data[0]

    def _mark(status: str, **fields) -> dict:
        store = _supabase()
        payload = {"status": status, **fields}
        return store._client.table("books").update(payload).eq("id", book_id).execute().data

    book = ctx.step.run("load-book", _load_book)
    ctx.step.run("mark-generating", lambda: _mark("generating"))

    # Stages below are stubs until the W4 input flows define the real pipeline.
    # Each step.run boundary makes the stage idempotent across retries.
    ctx.step.run("analyze", lambda: {"todo": "analyze stage", "input_kind": book.get("input_kind")})
    ctx.step.run("characters", lambda: {"todo": "character images"})
    ctx.step.run("scenes", lambda: {"todo": "scene segmentation"})
    ctx.step.run("illustrate", lambda: {"todo": "consistent scenes"})

    ctx.step.run("mark-ready", lambda: _mark("ready"))
    return {"book_id": book_id, "status": "ready"}


functions: list[inngest.Function] = [book_generate]
