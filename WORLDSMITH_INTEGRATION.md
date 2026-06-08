# Worldsmith integration — swap this app's narrative brain to the worldsmith engine

> Brief for a fresh Claude working in **this** repo (`book-generation`). Written
> 06/06/2026. Covers **C1 + C2** of Worldsmith Phase 2.5. Self-contained — you do
> not need the prior conversation.

## TL;DR

`book-generation` keeps its **body** (the `/create/*` flows, the Gemini/stitch
image pipeline, the Supabase data model, the Inngest worker, the reading UX). We
**replace its narrative brain** — the EPUB chapter-analysis → scenes pipeline that
invents story content — with calls to **Worldsmith**, a headless worldbuilding
engine that builds the story **canon** (cast, places, keepsakes, the ordered
story-beat arc, text appearance specs). This app then renders that canon into an
illustrated book exactly as it renders today.

This is the design intent of both projects: Worldsmith is a product-agnostic
engine; `book-generation` is its bedtime-stories consumer. Building this proves the
engine is genuinely consumer-agnostic.

## Why (context you can trust without re-deriving)

- **Worldsmith** lives at `/home/john/Projects/worldsmith` (a separate repo —
  **do not edit it from here**; if the engine needs a change, that's a worldsmith
  task, not a book-generation one). It is headless: **stores text/JSON only,
  generates no media.** Consumers reach it only over an HTTP/JSON + SSE API.
- The engine's read/drive contract is documented at
  `/home/john/Projects/worldsmith/docs/consumer-api.md` — **read it first.** It
  is the source of truth for endpoints, SSE event shapes, and canon shapes. The
  machine-readable version is the engine's `GET /openapi.json`.
- Image generation stays here (Worldsmith decision D10): the engine produces a
  **text** appearance spec per character; our pipeline draws from it. Likewise the
  parent's uploaded drawing/photo is converted to **text** persona attributes
  **here** (vision/transcription) and fed to the engine as part of the prompt —
  the engine ingests text only.

## The seam — what to keep vs replace

| File / area | Today | After |
|---|---|---|
| `worker/jobs.py` `book_generate` | branches on `input_kind` → **stub** page generators (`_generate_write` etc.) writing placeholder pages | calls the new Worldsmith stage, then the existing image stages, writing real pages |
| `pipeline/analyze.py` (EPUB → `analysis.json` via `ChapterAnalyzer`/Bedrock) | narrative brain | **replaced** by Worldsmith canon (do not delete yet; the CLI/EPUB path can keep using it) |
| `pipeline/scenes.py` (analysis → `scenes.json` via `SceneSegmentation`) | narrative brain | **replaced** by Worldsmith's ordered `story_beat` arc |
| `pipeline/characters.py` (Gemini character images) | **keep** — the body | unchanged; now fed canon-derived character prompts + appearance spec |
| `pipeline/illustrate.py` / `scenes` rendering | **keep** — the body | unchanged; now fed canon-derived scenes |
| `pipeline/storage.py` (Supabase `books`/`pages`) | **keep** | unchanged |

The cut is clean because the downstream image stages consume an intermediate shape
(`analysis.json` characters + `scenes.json` scenes). The new Worldsmith stage's job
is to **produce that same intermediate shape from canon**, so the image stages run
unchanged.

## Driving model: autonomous batch

The parent gives a framing + uploads a drawing/photo, clicks once. The Inngest
worker runs the engine in **`mode: "autonomous"`** (one-shot; no human-in-the-loop
mid-generation), reads the finished canon, renders, and writes pages. No live
streaming UI in this phase (that's a later enhancement).

---

## C1 — Typed Worldsmith client (in this repo)

Add a small Python client the worker uses to talk to the engine. The worker is
Python (`worker/`, `pipeline/`), so this is a Python module (e.g.
`pipeline/worldsmith_client.py`), **not** a TS client.

Requirements:

1. **Config from env:** `WORLDSMITH_BASE_URL` (default `http://127.0.0.1:8000` for
   local dev) and optional `WORLDSMITH_TOKEN` (a Cognito M2M bearer; omitted in
   local **open mode**). When present, send `Authorization: Bearer <token>`.
2. **Methods** (mirror `consumer-api.md`):
   - `create_world(pack_id, pack_version) -> world_id` (`POST /worlds`).
   - `run_agent(world_id, prompt, pack_id, mode="autonomous") -> None` — `POST
     /run_agent`, an SSE stream. **Consume the stream to completion**: read
     `mutation`/`token` events; stop on `done`; raise on `error`. (You can ignore
     token text in batch; you just need the turn to finish.)
   - `query_graph(world_id, at_seq=None, focus=None) -> GraphSnapshot` (`GET
     /worlds/{id}/graph`) — returns `{world_id, seq, nodes[], edges[]}`.
   - `healthz() -> {status, version}` for a connection preflight.
3. **Types:** model the canon shapes (`WorldNode`, `WorldEdge`, `GraphSnapshot`)
   as Pydantic models or TypedDicts so the mapping code is typed. Optionally
   codegen from `GET /openapi.json` instead of hand-writing — your call; hand-
   writing the four shapes you actually read is fine and lighter.
4. **SSE:** use `httpx` streaming (the repo already uses httpx-style clients) and
   parse `event:`/`data:`/`id:` lines. Keep it dependency-light.

**C1 acceptance:** against a locally-running engine (see *Running the engine*
below), a tiny script can `create_world("bedtime", "0.1.0")`, `run_agent(...)` a
prompt to completion, and `query_graph(...)` back a snapshot whose `nodes` include
`character` and `story_beat` types.

## C2 — Swap the brain in the worker

Replace the stub generators with a real Worldsmith-backed flow.

1. **New stage** `pipeline/worldsmith.py` with `run(book: dict) -> dict` that:
   - Derives the **prompt** and **persona attributes** from the `book` row: the
     framing/sentence/dream from `input_payload`, plus any text extracted from an
     uploaded drawing/photo (photo→text is a consumer step; a stub/manual text is
     acceptable for first cut, with a TODO for the vision call).
   - `create_world("bedtime", "0.1.0")` → `run_agent(world_id, prompt,
     "bedtime", mode="autonomous")` → `query_graph(world_id)`.
   - **Maps canon → the intermediate book shape** (see mapping below): characters
     (with `attributes.appearance`) and ordered scenes, in the structure
     `pipeline/characters.py` + the scene/illustrate stage already expect.
2. **Wire `worker/jobs.py`:** in `book_generate`, replace the `input_kind` → stub
   generator dispatch with: `pipeline.worldsmith.run(book)` to get the
   canon-derived intermediate, then the existing image stages, then build the
   `pages: list[dict]` (`{page_idx, text, image_url, image_status}`) and
   `upsert_pages` as today. Keep the `mark("generating") → … → mark("ready")`
   step structure and Inngest retries.
3. Keep the `input_kind` branch only where inputs genuinely differ (photo/drawing
   add an image→text step before the shared Worldsmith call); the narrative
   generation itself is now one shared path.

### Canon → book mapping (bedtime pack)

The `bedtime` pack's canon (see `consumer-api.md` and the engine's
`worldsmith/packs/bedtime/pack.yaml`) maps almost one-to-one:

- **Pages** = `story_beat` nodes ordered by the `follows` edge. Each beat has
  `attributes.phase` ∈ `opening → adventure → wobble → comfort → sleep`. Beat
  `summary`/`label` is the page text seed.
- **Cast** = `character` nodes. Each carries its **text appearance spec** under
  `attributes.appearance` = `{description, features{}}` (engine-fixed key
  `"appearance"`). Feed this to the character-image prompter for consistent art.
- **Which characters on a page** = `appears_in` edges (`character → story_beat`).
- **Page setting** = the `place` node linked to the beat by `set_in`
  (`story_beat → place`); `place.attributes` has `setting`/`mood`.
- **Props** = `keepsake` nodes via `holds` (`character → keepsake`).

### C2 acceptance

- A `book` row with `input_kind="write"` and a framing, when its `book.generate`
  Inngest event runs, produces a book whose **pages come from Worldsmith canon**
  (ordered beats), with **character art conditioned on the engine's appearance
  spec**, written to Supabase `pages`, and the book marked `ready`.
- The placeholder/stub text (`"…ikke koblet til pipeline ennå"`) is gone.
- No Worldsmith/engine code was modified from this repo.

## Running the engine locally (for dev + acceptance)

From the worldsmith repo (`/home/john/Projects/worldsmith`), open mode, no auth:

```bash
# throwaway Postgres
docker run -d --rm -e POSTGRES_PASSWORD=ws -e POSTGRES_USER=ws \
  -e POSTGRES_DB=worldsmith -p 5432:5432 postgres:16-alpine
# serve the engine on :8000 (bedtime pack pre-registered)
uv run python -m worldsmith.api.dev
curl -s localhost:8000/healthz          # {"status":"ok","version":"..."}
curl -s localhost:8000/packs            # includes {"pack_id":"bedtime","version":"0.1.0"}
```

`POST /run_agent` needs model creds (Bedrock or OpenRouter) configured in the
worldsmith `.env`; world/query endpoints work without them. Point this app at the
engine with `WORLDSMITH_BASE_URL=http://127.0.0.1:8000`.

## Out of scope for this brief

- C3–C5 polish (rich input→persona extraction, full reading-UX wiring, recurring
  persistent per-child worlds) — later.
- Live-stream / HITL interactive generation — later.
- Any change to the Worldsmith engine itself — that's a separate repo and a
  separate task. If you hit a missing engine capability, write it down for a
  worldsmith change; do not work around it by leaking rendering into the engine.
