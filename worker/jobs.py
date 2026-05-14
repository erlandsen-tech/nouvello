"""Inngest function definitions (PLAN.md W3 + W9).

`book.generate` runs the picture-book pipeline for one book row in Supabase.
Branches on `books.input_kind` to dispatch to a flow-specific generator.

Real per-flow generators are TODO — today every input_kind runs the same stub
that writes N placeholder pages. This is enough to exercise the end-to-end
plumbing (Next.js → Inngest → Fly worker → Supabase pages → viewer) so the
W4 frontend tasks can land in parallel. Replacing the stubs with real
`pipeline/` calls is a follow-up task.
"""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

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


# --- stub page generators (one per input_kind) ----------------------------
# Each returns a list of {page_idx, text, image_url?} dicts. Real
# implementations will wire into pipeline/ stages.

def _stub_pages(book: dict, lead: str) -> list[dict]:
    title = book.get("title") or "Eventyret"
    return [
        {
            "page_idx": i,
            "text": f"Side {i + 1} av «{title}» — {lead}",
            "image_status": "pending",
        }
        for i in range(5)
    ]


def _generate_write(book: dict) -> list[dict]:
    return _stub_pages(book, "tekst-flyten er ikke koblet til pipeline ennå.")


def _generate_guided(book: dict) -> list[dict]:
    return _stub_pages(book, "veiledet flyt — pipeline kommer.")


def _generate_photo(book: dict) -> list[dict]:
    return _stub_pages(book, "foto-flyten kobles til Gemini-conditioning senere.")


def _generate_drawing(book: dict) -> list[dict]:
    return _stub_pages(book, "tegning-flyt — style-transfer kommer.")


_GENERATORS = {
    "write": _generate_write,
    "guided": _generate_guided,
    "photo": _generate_photo,
    "drawing": _generate_drawing,
}


# --- helpers ---------------------------------------------------------------

def _load_book(book_id: str) -> dict:
    store = _supabase()
    resp = store._client.table("books").select("*").eq("id", book_id).execute()
    if not resp.data:
        raise ValueError(f"book {book_id} not found")
    return resp.data[0]


def _mark(book_id: str, status: str, **fields: Any) -> dict:
    store = _supabase()
    payload = {"status": status, **fields}
    resp = (
        store._client.table("books")
        .update(payload)
        .eq("id", book_id)
        .execute()
    )
    return resp.data[0] if resp.data else {}


def _write_pages(book_id: str, pages: list[dict]) -> int:
    store = _supabase()
    store.upsert_pages(UUID(book_id), pages)
    return len(pages)


# --- function -------------------------------------------------------------

@inngest_client.create_function(
    fn_id="book-generate",
    trigger=inngest.TriggerEvent(event="book.generate"),
    retries=2,
)
def book_generate(ctx: inngest.Context) -> dict:
    """Generate a picture book.

    Event payload: `{"book_id": "<uuid>"}`. The book row must already exist
    (created by `POST /api/books` from the Next.js side).
    """
    book_id: str = ctx.event.data["book_id"]

    book = ctx.step.run("load-book", lambda: _load_book(book_id))
    ctx.step.run("mark-generating", lambda: _mark(book_id, "generating"))

    input_kind: str = book.get("input_kind") or "write"
    generator = _GENERATORS.get(input_kind)
    if generator is None:
        raise ValueError(f"unknown input_kind {input_kind!r} for book {book_id}")

    pages = ctx.step.run(f"generate-{input_kind}", lambda: generator(book))
    page_count = ctx.step.run(
        "write-pages",
        lambda: _write_pages(book_id, pages),
    )

    ctx.step.run(
        "mark-ready",
        lambda: _mark(book_id, "ready", page_count=page_count),
    )
    return {"book_id": book_id, "status": "ready", "page_count": page_count}


functions: list[inngest.Function] = [book_generate]
