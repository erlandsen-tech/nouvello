# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> The repo is mid-pivot from a CLI prototype (EPUB → React-app book viewer) into a SaaS picture-book maker for parents. **Read `PLAN.md` first** — it captures the target architecture, workstream sequencing, and what's been done vs. what's still planned. Other doc references at root: `PERFORMANCE.md`, `BACKEND_SETUP.md`, `FRONTEND_BACKEND_INTEGRATION.md`, `STYLE_GUIDE.md`, `STYLE_SYSTEM.md`.

## Running code

- **Use the project venv.** `requirements.txt` is the manifest — install with `uv pip install -r requirements.txt` into `.venv` (per `.cursorrules`: never call a global `pip`; use `uv pip` or `python -m pip`).
- The previous setup was a venv-without-manifest that broke when the OS upgraded Python. If `.venv/bin/python` doesn't see the installed packages, you've hit that — recreate with `uv venv --python 3.14 .venv && uv pip install -r requirements.txt`.
- Activate with `source .venv/bin/activate`, or invoke directly: `.venv/bin/python script.py`.
- Secrets live in `.env` (gitignored), loaded via `python-dotenv`. `GEMINI_API_KEY` is required for any image-generation step; AWS credentials (env, profile, or instance role) are required for chapter analysis via Bedrock.

## Common commands

End-to-end pipeline (EPUB → JSON+PNG bundle → React-app book):
```bash
.venv/bin/python book_to_vn.py books/alice.epub --chapters demo
.venv/bin/python book_to_vn.py books/alice.epub --resume-from scenes      # resume mid-pipeline
.venv/bin/python book_to_vn.py books/alice.epub --style "horror gothic"   # apply a style override
```
Step keywords for `--resume-from`: `parse`, `analyze`, `characters`, `scenes`, `consistent`, `copy`, `update`. Chapter selection: comma list (`1,3,5`) or keywords (`demo`, `story`, `first`, `all`).

Individual stages (each script is a usable entry point — `book_to_vn.py` shells into them via `subprocess.run`, and W1 of the plan replaces this with in-process calls):
```bash
.venv/bin/python analyze_chapters.py books/alice.epub -c 0-2 -o output
.venv/bin/python generate_character_images.py --analysis output/alice_analysis.json -o output
.venv/bin/python ai/scene_segmentation.py output/alice output/alice
.venv/bin/python ai/consistent_scene_generator.py --scenes output/alice/scenes.json --characters output/alice/images -o output/alice/consistent_scenes
.venv/bin/python generate_environment_images.py output/alice [--variations]
```

Frontend (React 19 + CRA, in `frontend/`):
```bash
cd frontend && npm start          # dev server on :3000
cd frontend && npm run build
cd frontend && npm test
```

Backend (Flask CRUD over `books.json`, in `backend/`):
```bash
./start_backend.sh                       # convenience: activates venv, installs deps if missing, starts on :5000
.venv/bin/python backend/api.py          # equivalent direct invocation
```

## Architecture

A multi-stage pipeline that converts EPUBs into a browsable React app. Stages are decoupled — each writes its output as JSON/PNG to `output/<book>/` so any step can be re-run in isolation. The plan replaces this CLI flow with a FastAPI worker + Inngest + Supabase stack; until that lands, the CLI is canon.

**Pipeline orchestrator: `book_to_vn.py`.** Today it shells out to four per-stage scripts via `subprocess.run` (lines ~261, 312, 359, 596). The seven steps are: `parse → analyze → characters → scenes → consistent → copy → update`. Steps `copy` and `update` mirror artifacts into `frontend/public/{data,images}/` and append the book to `frontend/public/data/books.json` (the manifest the React app reads).

**`ai/` — analysis + generation engine.** Roughly two layers:
- *LLM layer*: `llm_providers.py` (provider abstraction over Bedrock + OpenAI; default Bedrock model is the EU Claude Sonnet 4.5 inference profile), `chapter_analyzer.py`, `epub_parser.py`, `chapter_patterns.py`, `ai_chapter_detector.py`, `hybrid_chapter_detector.py`, `cache_manager.py` (file-based sha256 cache for LLM responses).
- *Image layer*: `gemini_image_generator.py` wraps `google-genai` (`gemini-2.5-flash-image`). `character_image_prompter.py` builds character prompts from analysis; `expression_prompter.py` generates a fixed set of facial-expression variants per character; `consistent_scene_generator.py` is meant to feed character PNGs into Gemini as conditioning to keep the same character recognizable across scenes (verify this actually passes images via `contents=[...]`, not just in the prompt text — see PLAN.md W1); `environment_image_generator.py` produces backgrounds; `scene_segmentation.py` chunks a chapter into 8–15 visual scenes with prompts.

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

**`frontend/` — CRA + TypeScript reader.** `App.tsx` toggles between `BookChooser` (lists `books.json`) and `BookReader` (driven by `dataLoader.ts` which fetches `analysis.json` + `scenes.json` for a book id). Components: `BookChooser`, `BookReader`, `Navigation`, `TextPanel`, `ImagePanel`. PLAN.md W4 replaces this with a Next.js 15 app under `web/`.

**`backend/api.py` — Flask + flask-cors.** Tiny service that serves `books.json` and handles `DELETE /api/books/<id>` (removes the book from `books.json` and rmtree's both `output/<id>/` and `frontend/public/data/<id>/`, plus matching images). The React app calls this; the Python pipeline does not. PLAN.md W2 replaces this entirely with Supabase + Next.js API routes.

## Conventions baked into the codebase

- **Per-stage scripts add `ai/` to `sys.path` themselves** (`sys.path.insert(0, ...)`) and import modules unqualified (`from epub_parser import ...`). When adding a new pipeline step, follow that pattern rather than introducing package-style imports — the existing scripts are launched both standalone and via `subprocess` from `book_to_vn.py`.
- **Book name normalization:** `BookToVNConverter` derives `book_name` as `epub_path.stem.lower().replace(' ', '_')`. The same slug is used as the directory under `output/`, the data dir under `frontend/public/data/`, and the `id` in `books.json`. Keep that consistent or the React app silently won't find the book.
- **`--resume-from` is the debugging tool.** Each stage's outputs are idempotent files under `output/<book>/`, so re-running a single step is preferred over end-to-end re-runs (Gemini calls are slow and metered).
- **`.cursorrules` policy:** don't proactively create new `*.md` / README / quickstart files, don't spawn helper-script variants for things that already work — implement in existing files and explain usage in chat.
