# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> The repo is mid-pivot from a CLI prototype (EPUB → React-app book viewer) into a SaaS picture-book maker for parents (**Drømmevev**). **Read `PLAN.md` first** — it tracks the target architecture and workstream status (W1–W3 landed, W4 in progress). The new stack lives in `web/` (Next.js), `worker/` (FastAPI + Inngest), and Supabase; the old CLI (`book_to_vn.py`, `ai/`, `frontend/`, `backend/`) still works and is canon for local EPUB processing. Doc map — current: `PLAN.md`, `WORLDSMITH_INTEGRATION.md`, `STYLE_GUIDE.md`, `STYLE_SYSTEM.md`, `PERFORMANCE.md`; obsolete (Flask/CRA era, superseded by Supabase + Next.js): `BACKEND_SETUP.md`, `FRONTEND_BACKEND_INTEGRATION.md`.

## Running code

- **Use the project venv.** `requirements.txt` is the manifest — install with `uv pip install -r requirements.txt` into `.venv` (per `CURSOR.md`: never call a global `pip`; use `uv pip` or `python -m pip`).
- The previous setup was a venv-without-manifest that broke when the OS upgraded Python. If `.venv/bin/python` doesn't see the installed packages, you've hit that — recreate with `uv venv --python 3.14 .venv && uv pip install -r requirements.txt`.
- Activate with `source .venv/bin/activate`, or invoke directly: `.venv/bin/python script.py`.
- Secrets live in `.env` (gitignored), loaded via `python-dotenv`. `GEMINI_API_KEY` is required for any image-generation step; AWS credentials (env, profile, or instance role) are required for chapter analysis via Bedrock. The CLI `sync` step and the worker also need `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`. The Next.js app reads its own `web/.env.local` (`NEXT_PUBLIC_SUPABASE_*`, `INNGEST_DEV`).

## Common commands

End-to-end pipeline (EPUB → JSON+PNG bundle → React-app book):
```bash
.venv/bin/python book_to_vn.py books/alice.epub --chapters demo
.venv/bin/python book_to_vn.py books/alice.epub --resume-from scenes      # resume mid-pipeline
.venv/bin/python book_to_vn.py books/alice.epub --style "horror gothic"   # apply a style override
```
Step keywords for `--resume-from`: `parse`, `analyze`, `characters`, `scenes`, `consistent`, `copy`, `update`, `sync` (`sync` = push to Supabase, W2). Chapter selection: comma list (`1,3,5`) or keywords (`demo`, `story`, `first`, `all`).

Individual stages (each script is still a usable standalone entry point; `book_to_vn.py` now calls the `pipeline/` package in-process — W1 landed, the old `subprocess.run` chain is gone):
```bash
.venv/bin/python analyze_chapters.py books/alice.epub -c 0-2 -o output
.venv/bin/python generate_character_images.py --analysis output/alice_analysis.json -o output
.venv/bin/python ai/scene_segmentation.py output/alice output/alice
.venv/bin/python ai/consistent_scene_generator.py --scenes output/alice/scenes.json --characters output/alice/images -o output/alice/consistent_scenes
.venv/bin/python generate_environment_images.py output/alice [--variations]
```

SaaS stack (the new architecture — see PLAN.md; `web/` uses npm):
```bash
cd web && npm run dev                                      # Next.js 16 frontend on :3000
.venv/bin/uvicorn worker.main:app --reload --port 8000    # FastAPI worker; Inngest served at /api/inngest
npx inngest-cli@latest dev                                 # local Inngest dev server on :8288 (separate terminal)
```

Deprecated (old CRA reader + Flask CRUD; still runnable, retired when W4 lands):
```bash
cd frontend && npm start                  # CRA reader on :3000
./start_backend.sh                        # Flask CRUD over books.json on :5000
```

## Architecture

A multi-stage pipeline that converts EPUBs into a browsable book. Stages are decoupled — each writes its output as JSON/PNG to `output/<book>/` so any step can be re-run in isolation. The SaaS rewrite (Next.js `web/` + FastAPI `worker/` + Inngest + Supabase) is partially landed (W1–W3); the CLI remains canon for local EPUB processing.

**Pipeline orchestrator: `book_to_vn.py`.** It calls the `pipeline/` package (`analyze`, `characters`, `scenes`, `illustrate`, `storage`) as in-process functions — W1 removed the old `subprocess.run` chain. Steps: `parse → analyze → characters → scenes → consistent → copy → update → sync`. `copy`/`update` mirror artifacts into `frontend/public/{data,images}/` and append the book to `frontend/public/data/books.json` (the manifest the old React app reads); `sync` (W2) pushes books/pages to Supabase via `pipeline/storage.py`.

**`ai/` — analysis + generation engine.** Roughly two layers:
- *LLM layer*: `llm_providers.py` (provider abstraction over Bedrock + OpenAI; default Bedrock model is the EU Claude Sonnet 4.5 inference profile), `chapter_analyzer.py`, `epub_parser.py`, `chapter_patterns.py`, `ai_chapter_detector.py`, `hybrid_chapter_detector.py`, `cache_manager.py` (file-based sha256 cache for LLM responses).
- *Image layer*: `gemini_image_generator.py` wraps `google-genai` (`gemini-2.5-flash-image`). `character_image_prompter.py` builds character prompts from analysis; `expression_prompter.py` generates a fixed set of facial-expression variants per character; `consistent_scene_generator.py` feeds character PNGs into Gemini as conditioning (via `contents=[...]`, verified in W1) to keep the same character recognizable across scenes; `environment_image_generator.py` produces backgrounds; `scene_segmentation.py` chunks a chapter into 8–15 visual scenes with prompts.

**Per-stage parallelism.** The image-gen and scene-segmentation stages use `ThreadPoolExecutor` internally (`gemini_image_generator.py:336`, `consistent_scene_generator.py:138`, `scene_segmentation.py:179`+`540`) — non-obvious because the script CLIs look sequential. **Do not call `signal.SIGALRM` from anywhere reachable inside these workers** (it crashes outside the main thread); `ai/llm_providers.py` currently does this and it's a known bug.

**`output/<book_name>/` — canonical artifact layout.** Every downstream stage reads from here:
```
analysis.json              # ChapterAnalysis[] from the LLM
character_prompts.json     # Per-character image prompt + sprite paths
scenes.json                # SceneSegment[] with image_prompt, characters_present
images/                    # Character sprites + expression variants
consistent_scenes/         # Per-scene composites with consistent characters
environments/              # Background-only renders
prompts/, chapters/        # Optional debug / per-chapter exports
```
The React app expects a *mirrored* copy under `frontend/public/data/<book>/` and image files flat under `frontend/public/images/{characters,scenes,environments}/`. The `copy` step in `book_to_vn.py` performs that mirror. Caches live under `.cache/` (gitignored).

**`web/` — Next.js 16 (App Router) frontend.** Canon going forward (W4, in progress). `src/app/create/{write,guided,photo,drawing}/` are the four story-input flows; also `/library`, `/book/[id]` (viewer), magic-link auth under `/auth`, and `api/books/route.ts` which enqueues an Inngest event. `src/lib/supabase/{server,browser}.ts` are `@supabase/ssr` clients.

**`worker/` — FastAPI + Inngest (Fly.io).** `main.py` serves Inngest at `/api/inngest`; `jobs.py` defines the `book.generate` function. **W3 skeleton only** — the per-input generator steps still write placeholder pages; real `pipeline/` wiring is pending W4. Deploy target `drommevev-worker` (Fly region `ams`); secrets: `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `INNGEST_SIGNING_KEY`, `INNGEST_EVENT_KEY`.

**Supabase (W2, done).** Schema in `db/schema.sql` (+ migration `db/20260513170000_initial.sql`). Tables: `users`, `books`, `pages`, `jobs`, `purchases`; RLS per user; private storage buckets `book-images/`, `child-photos/`, `book-pdfs/`. The worker uses the service-role key; the CLI `sync` step uses `pipeline/storage.py`.

**Worldsmith (narrative brain).** `pipeline/worldsmith_client.py` + `pipeline/worldsmith.py` drive a separate headless engine (its own repo at `/home/john/Projects/worldsmith` — **do not edit it from here**) to build the story canon, which `worker/jobs.py` maps into the image stages. C1+C2 landed (`16fb2c5`); see `WORLDSMITH_INTEGRATION.md` (brief) + `WORLDSMITH_HANDOVER.md` (current state, run instructions, open issues). Photo/drawing persona extraction (C3) is still stubbed.

**Old reader/API (deprecated).** `frontend/` is the CRA+TypeScript reader (`App.tsx` toggles `BookChooser`/`BookReader`, driven by `dataLoader.ts`); `backend/api.py` is a Flask service serving `books.json` + `DELETE /api/books/<id>`. Both are superseded by `web/` + Supabase and will be removed when W4 lands.

## Conventions baked into the codebase

- **Per-stage scripts add `ai/` to `sys.path` themselves** (`sys.path.insert(0, ...)`) and import modules unqualified (`from epub_parser import ...`). When adding a new pipeline step, follow that pattern rather than introducing package-style imports — the existing scripts are launched both standalone and via `subprocess` from `book_to_vn.py`.
- **Book name normalization:** `BookToVNConverter` derives `book_name` as `epub_path.stem.lower().replace(' ', '_')`. The same slug is used as the directory under `output/`, the data dir under `frontend/public/data/`, and the `id` in `books.json`. Keep that consistent or the React app silently won't find the book.
- **`--resume-from` is the debugging tool.** Each stage's outputs are idempotent files under `output/<book>/`, so re-running a single step is preferred over end-to-end re-runs (Gemini calls are slow and metered).
- **`CURSOR.md` policy:** don't proactively create new `*.md` / README / quickstart files, don't spawn helper-script variants for things that already work — implement in existing files and explain usage in chat.
