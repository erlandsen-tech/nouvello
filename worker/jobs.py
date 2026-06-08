"""Inngest function definitions (PLAN.md W3 + W9; WORLDSMITH_INTEGRATION.md C2).

`book.generate` runs the picture-book pipeline for one book row in Supabase:
derive a prompt from the input flow → Worldsmith builds the story canon →
map canon to the intermediate shapes → render character + scene images
(`pipeline.characters` / `pipeline.illustrate`) → upload to Supabase Storage →
write `pages`. The narrative brain is Worldsmith; the image body is unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import UUID

import inngest

from pipeline import characters as _characters
from pipeline import illustrate as _illustrate
from pipeline import storage as _storage
from pipeline import worldsmith as _worldsmith


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


# --- generation ------------------------------------------------------------
# One shared narrative path (Worldsmith) for every input_kind; the per-kind
# difference is only in how the prompt/persona is derived (see pipeline.worldsmith,
# which for photo/drawing folds in an image→text persona step).

def _scene_filename(title: str, scene_number: int) -> str:
    """Replicate ConsistentSceneGenerator's *local* output naming (may contain non-ASCII)."""
    safe = title.lower().replace(" ", "_").replace("-", "_").replace("'", "").replace('"', "")
    safe = "".join(c for c in safe if c.isalnum() or c == "_")
    return f"scene_{scene_number:02d}_{safe}.png"


def _ascii_key(name: str) -> str:
    """Supabase Storage keys must be ASCII; transliterate Norwegian chars, drop the rest.

    `str.isalnum()` treats æ/ø/å as alphanumeric, so they survive into local filenames
    (fine on disk) but Supabase rejects them as InvalidKey — common for nb-NO titles.
    """
    name = name.translate(str.maketrans({
        "æ": "ae", "ø": "o", "å": "a", "Æ": "Ae", "Ø": "O", "Å": "A",
    }))
    return name.encode("ascii", "ignore").decode("ascii")


def _generate(book: dict) -> list[dict]:
    """Run the full pipeline for one book and return its `pages` rows.

    Kept inside a single Inngest step so the on-disk working tree stays coherent
    across the Worldsmith → render → upload sub-stages; it is idempotent on retry
    (image files are skipped when present, uploads upsert).
    """
    inter = _worldsmith.run(book)

    # Character images from the canon-derived prompts (style stays out of the
    # filenames so the scene stage's character-ref lookup finds `<Name>.png`).
    _characters.run(inter["analysis_path"], inter["output_base"])

    # Scene illustrations conditioned on the character reference images.
    _illustrate.run(
        inter["scenes_path"],
        inter["images_dir"],
        inter["scenes_out_dir"],
        art_style=inter["art_style"],
    )

    return _build_pages(book, inter)


def _build_pages(book: dict, inter: dict) -> list[dict]:
    """Upload rendered images to Supabase Storage (ASCII keys) and map scenes → page rows."""
    store = _supabase()
    prefix = f"{book['user_id']}/{book['id']}"

    def _upload_pngs(local_dir: str, sub: str) -> dict[str, str]:
        """Upload every PNG; return {local_filename: ascii_storage_key}."""
        keys: dict[str, str] = {}
        for path in sorted(Path(local_dir).glob("*.png")):
            key = f"{prefix}/{sub}/{_ascii_key(path.name)}"
            store.upload_file(_storage.BUCKET_BOOK_IMAGES, key, path)
            keys[path.name] = key
        return keys

    _upload_pngs(inter["images_dir"], "characters")
    scene_keys = _upload_pngs(inter["scenes_out_dir"], "scenes")

    pages: list[dict] = []
    for idx, scene in enumerate(inter["scenes"]):
        local_name = _scene_filename(scene["title"], scene["scene_number"])
        key = scene_keys.get(local_name)  # None if that scene image didn't render
        pages.append(
            {
                "page_idx": idx,
                "text": scene.get("content") or "",
                "image_url": key,
                "image_status": "done" if key else "pending",
            }
        )
    return pages


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

    try:
        pages = ctx.step.run("generate", lambda: _generate(book))
        page_count = ctx.step.run("write-pages", lambda: _write_pages(book_id, pages))
    except Exception as exc:
        ctx.step.run(
            "mark-failed",
            lambda: _mark(book_id, "failed", error=str(exc)[:500]),
        )
        raise

    ctx.step.run(
        "mark-ready",
        lambda: _mark(book_id, "ready", page_count=page_count),
    )
    return {"book_id": book_id, "status": "ready", "page_count": page_count}


functions: list[inngest.Function] = [book_generate]
