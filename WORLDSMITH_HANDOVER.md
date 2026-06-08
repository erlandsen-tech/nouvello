# Worldsmith integration — handover for a fresh session

> Written 2026-06-08. Picks up after **C1 + C2** of `WORLDSMITH_INTEGRATION.md`
> landed (commit `16fb2c5`). Self-contained — read this + `WORLDSMITH_INTEGRATION.md`
> and you're current. The narrative brain of `book-generation` is now the Worldsmith
> engine; the Gemini/Supabase "body" is unchanged.

## TL;DR — state

C1 (typed client) and C2 (canon→book mapping + worker wiring) are **implemented,
verified, and committed**. The full picture-book path works end to end with real
Gemini art. Two **engine-side** caveats and a few decisions remain before a clean
live frontend demo (see *Open issues*).

## What landed (commit `16fb2c5`)

| File | Role |
|---|---|
| `pipeline/worldsmith_client.py` | **C1** — typed httpx + SSE client: `healthz / create_world / run_agent / query_graph`. `run_agent` consumes the SSE stream to `done`, raises `WorldsmithError` on `error`. `from_env()` reads `WORLDSMITH_BASE_URL` (default `http://127.0.0.1:8000`) + optional `WORLDSMITH_TOKEN`. |
| `pipeline/worldsmith.py` | **C2** — `run(book)` derives a prompt/persona from `input_payload`, drives the engine autonomous, then maps canon → `character_prompts.json` + `scenes.json` (the shapes the image stages already consume). Pure mapping; no `ai/` imports. |
| `worker/jobs.py` | **C2** — `book_generate` now: `mark-generating → _generate (worldsmith.run → characters.run → illustrate.run → _build_pages: upload + map) → write-pages → mark-ready/failed`. Stub `_generate_*` removed. `_ascii_key()` makes Supabase keys ASCII. |
| `pipeline/__init__.py`, `requirements.txt` | register the stage; pin `httpx`. |
| `WORLDSMITH_INTEGRATION.md` | the original brief (C1–C5 scope), committed for reference. |

### The seam (unchanged from the brief)
`worldsmith.run` produces the **same intermediate shapes** the image body expects, so
`pipeline.characters` and `pipeline.illustrate` run untouched:
- `character` nodes (+ `attributes.appearance.{description,features}`) → `character_prompts.json`.
- `story_beat` nodes ordered by `follows` → `scenes.json`; `appears_in`→cast, `set_in`→setting, `holds`→props.
- Page text = beat `summary`; page image = `consistent_scenes/scene_NN_<title>.png`.

## How to run it locally

Four processes. **Port gotcha:** the Worldsmith engine owns `:8000`, so the worker
(whose docstring still says 8000) must use a different port.

```bash
# 1. Worldsmith engine (separate repo /home/john/Projects/worldsmith) — open mode on :8000
#    (docker pg + `uv run python -m worldsmith.api.dev`; see WORLDSMITH_INTEGRATION.md)
# 2. book-generation worker — NOT 8000:
.venv/bin/uvicorn worker.main:app --reload --port 8001
# 3. Inngest dev:
npx inngest-cli@latest dev
# 4. Next.js:
cd web && npm run dev
```

Env the worker needs (all in `.env`, loaded via the `ai/` import chain): `GEMINI_API_KEY`,
`GEMINI_MODEL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`. `WORLDSMITH_BASE_URL` is
**not** in `.env` — the client default `http://127.0.0.1:8000` is correct locally; set it
explicitly for Fly.io (W3 deploy) to the engine's remote URL.

Frontend path is fully wired (not stubs): `/create/write` → `POST /api/books` (inserts
`books` row + `inngest.send("book.generate")`) → worker → `pages`/images → `/book/[id]`
`BookViewer` polls every 2.5s, signs URLs, shows skeleton→art.

## Verified vs not

| | Status |
|---|---|
| C1 acceptance (live engine) | ✅ canon with character + story_beat |
| C2 mapping (live + synthetic) | ✅ ordering, cast/setting/props, dataclass round-trips |
| Render → Supabase upload → pages (real Gemini) | ✅ 3/3 pages, real art, book `ready`, signed URLs work |
| **Full live UI run (real engine, autonomous)** | ❌ blocked by engine flakiness (below) |

The render proof used a **fake Worldsmith client** with a canned canon to dodge engine
flakiness and prove the Gemini+Supabase leg deterministically (cheap, repeatable). That
pattern is the fastest way to test the body without burning engine turns.

## Open issues / decisions

1. **Engine autonomous mode is flaky** (worldsmith-repo fix, do NOT work around here):
   - intermittent `run_agent aborted: Response ended prematurely` (upstream model stream drops);
   - `multiple pending interrupts… specify the interrupt id when resuming` — autonomous
     mode shouldn't raise LangGraph HITL interrupts. Blocks a clean live UI generation.
2. **Two-arc ordering** — the engine sometimes emits two `opening→…→sleep` chains (two
   `follows` heads). `_order_beats` walks each chain and concatenates by phase. Decide:
   collapse to one canonical arc, pick the longest, or keep all. (`pipeline/worldsmith.py`)
3. **Imageless "ready" book** — if every image fails (e.g. quota), stages don't raise, so
   `_generate` still returns pages and the book marks `ready` with all pages `pending`.
   Consider failing the book when 0 images succeed. (`worker/jobs.py:_build_pages`)
4. **Port collision** `:8000` (engine vs worker) — worker docstring/PLAN still say 8000.
5. **`output/` is not gitignored** — pre-existing gap; test runs leave `output/<uuid>/`
   untracked. Consider adding `output/` to `.gitignore`.

## Uncommitted in the tree (intentionally left out of `16fb2c5`)

- `CLAUDE.md` — has this session's `/init` rewrite (documents the SaaS stack). Its
  "Worldsmith (planned) … Not yet implemented" line is now stale — flip it to "landed".
- `web/next.config.ts`, `web/src/app/{book,library}/`, `stitch_brief/` — pre-existing W4
  work, not part of C1+C2.
- `output/a4246ce1-…/` — disposable render-leg test artifact (has a `preview.html` you can open).

## Next steps

- **Commit `16fb2c5` is local** — push to `main` (trunk-based; see [[feedback-trunk-based]]).
- One real **frontend-driven** run through the actual Inngest runtime, once the engine's
  autonomous mode is stable.
- **C3** (brief): real image→text persona extraction for `/create/photo` + `/create/drawing`
  (currently a stubbed `TODO(C3)` in `pipeline/worldsmith._persona_text`).
- **C4/C5**: fuller reading-UX, persistent per-child worlds.
- PLAN.md roadmap unchanged: **W3** deploy worker to Fly.io · **W5** PDF · **W6** Stripe · **W7** safety.

## Gotchas worth knowing

- **Gemini key**: needs **billing enabled on the same Cloud project as the key**, and the
  image model has no free-tier quota. A wrong/free-tier key shows `429 free_tier limit: 0`
  or `400 API key expired`. The `AQ.`-prefixed key format works.
- **Supabase keys must be ASCII** — `æ/ø/å` pass `isalnum()` and reach local filenames but
  break storage keys; `_ascii_key()` handles it. Watch for this anywhere keys derive from titles.
- **Dev/RLS**: CLI + test runs use the lazily-provisioned `dev@drommevev.local` user; `pages`
  are RLS owner-gated, so test books aren't visible to your real web login.
- Memory index: see `memory/MEMORY.md`, esp. [[worldsmith-integration-c1-c2]] and [[project-status]].
