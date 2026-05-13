"""Supabase Storage + Postgres upload helpers (PLAN.md W2).

Used by the CLI today as an additive mirror; the W3 FastAPI worker will reuse the
same surface for the production write path.

The module is safe to import without Supabase configured — `from_env()` returns
`None` when the env vars are absent, letting callers no-op gracefully.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
from uuid import UUID, uuid5

from supabase import Client, create_client

BUCKET_BOOK_IMAGES = "book-images"
BUCKET_CHILD_PHOTOS = "child-photos"
BUCKET_BOOK_PDFS = "book-pdfs"

# Stable namespace used to derive a deterministic UUID from the CLI's book_name slug
# (so the same EPUB always maps to the same books.id during local dev).
_CLI_BOOK_NAMESPACE = UUID("c2e0a3b9-9b13-5b69-9c44-c110001cba01")
# Auth identity the CLI runs as — provisioned lazily via the admin API.
# The W3 worker uses the real owner from the books row instead.
DEV_USER_EMAIL = "dev@drommevev.local"


@dataclass
class UploadedAsset:
    bucket: str
    path: str          # bucket-relative key, e.g. "<user_id>/<book_id>/scene_01.png"


class SupabaseStore:
    """Thin wrapper around the official supabase-py client.

    All methods are sync and threadsafe — fine to call from inside the existing
    ThreadPoolExecutor pipelines in `ai/`.
    """

    def __init__(self, client: Client):
        self._client = client

    # -- construction ----------------------------------------------------

    @classmethod
    def from_env(cls) -> Optional["SupabaseStore"]:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            return None
        return cls(create_client(url, key))

    # -- storage ---------------------------------------------------------

    def upload_file(
        self,
        bucket: str,
        key: str,
        local_path: Path,
        *,
        content_type: Optional[str] = None,
    ) -> UploadedAsset:
        """Upload one file, overwriting any existing object at the same key."""
        if not local_path.exists():
            raise FileNotFoundError(local_path)
        if content_type is None:
            content_type = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
        self._client.storage.from_(bucket).upload(
            path=key,
            file=local_path,
            file_options={
                "content-type": content_type,
                "cache-control": "3600",
                "upsert": "true",
            },
        )
        return UploadedAsset(bucket=bucket, path=key)

    def upload_directory(
        self,
        bucket: str,
        prefix: str,
        local_dir: Path,
        *,
        patterns: Iterable[str] = ("*.png",),
    ) -> list[UploadedAsset]:
        if not local_dir.exists():
            return []
        results: list[UploadedAsset] = []
        for pattern in patterns:
            for path in sorted(local_dir.glob(pattern)):
                if path.is_file():
                    key = f"{prefix.rstrip('/')}/{path.name}"
                    results.append(self.upload_file(bucket, key, path))
        return results

    def signed_url(self, bucket: str, key: str, *, expires_in: int = 3600) -> str:
        resp = self._client.storage.from_(bucket).create_signed_url(key, expires_in)
        return resp["signedURL"] if isinstance(resp, dict) else resp.signed_url  # type: ignore[union-attr]

    # -- postgres --------------------------------------------------------

    def ensure_dev_user(self, email: str = DEV_USER_EMAIL) -> UUID:
        """Return a UUID for a CLI-only auth user, creating it on first call.

        Uses the auth admin API so the user is a real `auth.users` row — the
        `handle_new_auth_user` trigger then auto-provisions `public.users`.
        Memoized for the lifetime of this `SupabaseStore` instance.
        """
        cached = getattr(self, "_dev_user_id", None)
        if cached is not None:
            return cached

        for page in range(1, 11):                      # bound the scan; admin pages default to 50
            users = self._client.auth.admin.list_users(page=page, per_page=200)
            if not users:
                break
            for u in users:
                if getattr(u, "email", None) == email:
                    self._dev_user_id = UUID(u.id)
                    return self._dev_user_id
            if len(users) < 200:
                break

        created = self._client.auth.admin.create_user({
            "email": email,
            "email_confirm": True,
        })
        self._dev_user_id = UUID(created.user.id)
        return self._dev_user_id

    def upsert_book(self, book_id: UUID, user_id: UUID, **fields) -> dict:
        payload = {"id": str(book_id), "user_id": str(user_id), **_normalize(fields)}
        resp = self._client.table("books").upsert(payload).execute()
        return resp.data[0] if resp.data else {}

    def upsert_pages(self, book_id: UUID, pages: list[dict]) -> list[dict]:
        if not pages:
            return []
        payload = [
            {"book_id": str(book_id), **_normalize(p)} for p in pages
        ]
        resp = (
            self._client.table("pages")
            .upsert(payload, on_conflict="book_id,page_idx")
            .execute()
        )
        return resp.data or []


def book_id_from_slug(slug: str) -> UUID:
    """Stable UUID derived from a CLI book_name slug — same EPUB → same row."""
    return uuid5(_CLI_BOOK_NAMESPACE, slug)


def slugify_for_storage_key(value: str) -> str:
    """Storage object keys must avoid spaces and shell-hostile chars."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return cleaned or "untitled"


def push_book_artifacts(
    store: SupabaseStore,
    *,
    book_id: UUID,
    user_id: Optional[UUID],
    book_name: str,
    book_dir: Path,
    title: Optional[str] = None,
    art_style: Optional[str] = None,
) -> dict:
    """Mirror the CLI output tree (output/<book>/) into Supabase Storage + Postgres.

    Mirrors the surface of `BookToVNConverter._copy_to_react_app` so the local
    frontend mirror and the Supabase upload stay in step until W4 retires the mirror.
    `user_id=None` resolves to the lazily-provisioned CLI dev user.
    Returns a small summary dict for logging.
    """
    if user_id is None:
        user_id = store.ensure_dev_user()
    prefix = f"{user_id}/{book_id}"

    image_uploads: list[UploadedAsset] = []
    image_uploads += store.upload_directory(
        BUCKET_BOOK_IMAGES, f"{prefix}/characters", book_dir / "images"
    )
    scenes_dir = _pick_scenes_dir(book_dir, art_style)
    if scenes_dir is not None:
        image_uploads += store.upload_directory(
            BUCKET_BOOK_IMAGES, f"{prefix}/scenes", scenes_dir
        )
    image_uploads += store.upload_directory(
        BUCKET_BOOK_IMAGES, f"{prefix}/environments", book_dir / "environments"
    )

    scenes_json = _safe_load_json(book_dir / "scenes.json")
    page_rows: list[dict] = []
    if isinstance(scenes_json, list):
        for idx, scene in enumerate(scenes_json):
            safe = slugify_for_storage_key(str(scene.get("title", "scene"))).lower()
            scene_number = scene.get("scene_number", idx + 1)
            page_rows.append(
                {
                    "page_idx": idx,
                    "text": str(scene.get("text", "") or scene.get("description", "")),
                    "image_url": f"{prefix}/scenes/scene_{scene_number:02d}_{safe}.png",
                    "image_status": "done",
                }
            )

    derived_title = title or _safe_load_json(book_dir / "analysis.json", default={}).get("title")
    derived_title = derived_title or book_name.replace("_", " ").title()

    store.upsert_book(
        book_id=book_id,
        user_id=user_id,
        title=derived_title,
        status="ready",
        input_kind="write",                 # CLI flow doesn't know; closest match
        art_style=art_style,
        page_count=len(page_rows),
    )
    store.upsert_pages(book_id, page_rows)

    return {
        "book_id": str(book_id),
        "uploaded_assets": len(image_uploads),
        "page_rows": len(page_rows),
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _pick_scenes_dir(book_dir: Path, art_style: Optional[str]) -> Optional[Path]:
    if art_style:
        style_safe = "".join(c for c in art_style if c.isalnum() or c in " -_").strip()
        style_safe = style_safe.replace(" ", "_").lower()
        styled = book_dir / f"consistent_scenes_{style_safe}"
        if styled.exists():
            return styled
    default = book_dir / "consistent_scenes"
    return default if default.exists() else None


def _safe_load_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _normalize(fields: dict) -> dict:
    """Drop None values so we don't clobber existing rows with NULL on upsert."""
    return {k: v for k, v in fields.items() if v is not None}
