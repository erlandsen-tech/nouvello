"""Typed Worldsmith consumer client (WORLDSMITH_INTEGRATION.md, C1).

A dependency-light Python client the worker uses to drive the headless Worldsmith
worldbuilding engine over its HTTP/JSON + SSE API. Mirrors the read/drive contract
in `/home/john/Projects/worldsmith/docs/consumer-api.md`.

The engine stores text/JSON only and generates no media — this client creates a
world, runs the autonomous agent turn to completion, and reads back the folded
canon graph. Image generation stays consumer-side (Worldsmith decision D10).
"""

from __future__ import annotations

import json
import os
from typing import Any, Iterable, Iterator, List, Optional, TypedDict

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


# --- canon shapes (the four we actually read; see consumer-api.md) ----------

class WorldNode(TypedDict, total=False):
    id: str
    type: str                # bedtime: character | place | keepsake | story_beat
    label: str
    summary: str
    attributes: dict[str, Any]
    provenance: dict[str, Any]
    confidence: float
    draft: bool


class WorldEdge(TypedDict, total=False):
    id: str
    source: str
    target: str
    relation: str            # bedtime: appears_in | set_in | holds | follows | ...
    weight: float
    label: str
    provenance: dict[str, Any]


class GraphSnapshot(TypedDict, total=False):
    world_id: str
    seq: int
    nodes: List[WorldNode]
    edges: List[WorldEdge]


class HealthStatus(TypedDict, total=False):
    status: str
    version: str


class WorldsmithError(RuntimeError):
    """Raised when the engine returns an error or an agent turn aborts."""


class WorldsmithClient:
    """Thin sync client over the Worldsmith consumer API.

    Auth is optional: in local **open mode** no token is needed (the principal is
    ``"anonymous"`` and owns every world). When `WORLDSMITH_TOKEN` is set it is
    sent as a `Bearer` token — the browser must never hold it; only this
    server-side caller does.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        token: Optional[str] = None,
        connect_timeout: float = 10.0,
        read_timeout: float = 30.0,
        run_timeout: float = 600.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._run_timeout = run_timeout
        self._http = httpx.Client(
            timeout=httpx.Timeout(connect=connect_timeout, read=read_timeout, write=30.0, pool=10.0),
        )

    @classmethod
    def from_env(cls) -> "WorldsmithClient":
        return cls(
            base_url=os.getenv("WORLDSMITH_BASE_URL", DEFAULT_BASE_URL),
            token=os.getenv("WORLDSMITH_TOKEN") or None,
        )

    # -- context manager / lifecycle ------------------------------------

    def __enter__(self) -> "WorldsmithClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    # -- headers --------------------------------------------------------

    def _headers(self, *, sse: bool = False) -> dict[str, str]:
        headers = {"Accept": "text/event-stream" if sse else "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # -- endpoints ------------------------------------------------------

    def healthz(self) -> HealthStatus:
        """Liveness + engine version (unauthenticated)."""
        resp = self._http.get(f"{self.base_url}/healthz", headers=self._headers(), timeout=10.0)
        resp.raise_for_status()
        return resp.json()

    def create_world(
        self, pack_id: str, pack_version: str, *, world_id: Optional[str] = None
    ) -> str:
        """Pin a new world to a registered pack version → returns its world_id."""
        body: dict[str, Any] = {"pack_id": pack_id, "pack_version": pack_version}
        if world_id:
            body["world_id"] = world_id
        resp = self._http.post(f"{self.base_url}/worlds", json=body, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        wid = data.get("world_id") or data.get("id")
        if not wid:
            raise WorldsmithError(f"create_world: no world_id in response: {data!r}")
        return wid

    def run_agent(
        self,
        world_id: str,
        prompt: str,
        pack_id: str,
        *,
        mode: str = "autonomous",
        focus: Optional[List[str]] = None,
    ) -> None:
        """Drive one agent turn over SSE and consume the stream to completion.

        Reads `mutation`/`token` events, returns on `done`, raises on `error`.
        Token text is ignored in batch mode — we only need the turn to finish.
        """
        body: dict[str, Any] = {
            "world_id": world_id,
            "prompt": prompt,
            "pack_id": pack_id,
            "mode": mode,
        }
        if focus:
            body["focus"] = focus

        mutations = 0
        with self._http.stream(
            "POST",
            f"{self.base_url}/run_agent",
            json=body,
            headers=self._headers(sse=True),
            timeout=httpx.Timeout(connect=10.0, read=self._run_timeout, write=30.0, pool=10.0),
        ) as resp:
            resp.raise_for_status()
            for event, data, _ in _iter_sse(resp.iter_lines()):
                if event == "mutation":
                    mutations += 1
                elif event == "done":
                    return
                elif event == "error":
                    raise WorldsmithError(f"run_agent aborted: {data}")
        raise WorldsmithError(
            f"run_agent stream ended without 'done' (saw {mutations} mutations)"
        )

    def query_graph(
        self,
        world_id: str,
        *,
        at_seq: Optional[int] = None,
        focus: Optional[List[str]] = None,
    ) -> GraphSnapshot:
        """Folded read of a world's canon graph."""
        params: dict[str, Any] = {}
        if at_seq is not None:
            params["at_seq"] = at_seq
        if focus:
            params["focus"] = ",".join(focus)
        resp = self._http.get(
            f"{self.base_url}/worlds/{world_id}/graph",
            params=params,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# SSE parsing — a minimal text/event-stream decoder (event/data/id fields)
# ---------------------------------------------------------------------------

def _iter_sse(lines: Iterable[str]) -> Iterator[tuple[str, str, Optional[str]]]:
    """Yield `(event, data, id)` per SSE event. `data` joins multi-line payloads."""
    event: Optional[str] = None
    data: list[str] = []
    event_id: Optional[str] = None

    def flush() -> Optional[tuple[str, str, Optional[str]]]:
        if not data and event is None and event_id is None:
            return None
        return (event or "message", "\n".join(data), event_id)

    for raw in lines:
        line = raw.rstrip("\r")
        if line == "":
            out = flush()
            if out is not None:
                yield out
            event, data, event_id = None, [], None
            continue
        if line.startswith(":"):
            continue  # comment / heartbeat
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            event = value
        elif field == "data":
            data.append(value)
        elif field == "id":
            event_id = value

    out = flush()
    if out is not None:
        yield out
