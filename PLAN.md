# Productizing the picture-book maker — 1-2 month bootstrap plan

## Context

Today this repo is a **CLI prototype**: a Python pipeline that turns public-domain EPUBs into a JSON+PNG bundle and a CRA reader, run by hand on a laptop. Per the product decisions captured below, the new product is something else entirely:

- **Customer**: parents creating a personalized picture book with/for their kid.
- **Inputs (all four)**: typed/dictated story · guided prompt · photo of the kid as the hero · photo of the kid's drawing.
- **Output**: a polished, printable **PDF** (web preview + downloadable A4/Letter file with bleed).
- **Build profile**: 1-2 month bootstrap — proper job queue, cloud storage, paid product, charge $20+ per book confidently. EPUB-to-VN gets shelved as a future tier.
- **Performance is non-negotiable** — current pipeline is sequential `subprocess.run` chains and sequential Gemini calls; it won't survive a real customer.

The existing AI code (character prompter, expression prompter, consistent-scene generator, scene segmentation) is the **moat** and stays. The CLI orchestrator, `subprocess` glue, local file mirror, CRA reader, and `books.json` get replaced.

## North-star architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│ Next.js frontend    │     │ Next.js API routes   │     │ Stripe Checkout     │
│ (Vercel)            │────▶│ - auth, payments     │◀───▶│ + webhooks          │
│ - 4 creation flows  │     │ - book CRUD          │     └─────────────────────┘
│ - viewer + PDF link │     │ - signed-URL upload  │
└─────────┬───────────┘     └──────────┬───────────┘
          │                            │
          │ SSE / poll progress        │ enqueue job
          ▼                            ▼
┌─────────────────────┐     ┌──────────────────────┐
│ Inngest             │────▶│ FastAPI worker       │
│ - durable workflow  │     │ (Fly.io / Render)    │
│ - retry, fan-out    │     │ - reuses ai/* modules│
└─────────────────────┘     │ - async Gemini calls │
                            │ - PDF render         │
                            └──────────┬───────────┘
                                       │
                            ┌──────────▼───────────┐
                            │ Supabase             │
                            │ - Postgres (books,   │
                            │   pages, users,      │
                            │   credits, jobs)     │
                            │ - Storage (pngs,pdfs)│
                            │ - Auth (parents)     │
                            └──────────────────────┘
```

**Why this stack (and not others)**

- **Next.js (App Router) over CRA** — SSR/SEO for marketing, RSC for the viewer, Image component (AVIF + lazy + on-the-fly resize), API routes collapse a separate Flask service. CRA is on life-support; migrating it later costs more.
- **Keep Python for the AI pipeline** — `ai/character_image_prompter.py`, `ai/expression_prompter.py`, `ai/consistent_scene_generator.py`, `ai/scene_segmentation.py`, `ai/gemini_image_generator.py` are the product. Rewriting in TS in 8 weeks is not feasible. Run them behind a thin **FastAPI** worker.
- **Inngest over Celery/RQ** — durable steps, automatic retries, perfect for AI workflows that take 30-90s and fan out per page. Saves us from running Redis + a beat scheduler. Free tier covers MVP.
- **Supabase** — auth + Postgres + Storage in one. Replaces `books.json`, the local `output/` tree, and a hand-rolled login system. Row-Level Security keeps user data isolated for free.
- **Stripe Checkout (hosted)** — credit packs ("3 books for $39") + one-off ("buy this book — $19"). Hosted page = no PCI scope, ship in a day.

## What's already on `main` (as of plan rebase)

A "make generation faster" PR landed before this plan was committed. It already did several W1 items:

- `ai/gemini_image_generator.py` and `ai/consistent_scene_generator.py` and `ai/scene_segmentation.py` parallelize per-stage Gemini calls via `ThreadPoolExecutor`. Threads, not asyncio — for I/O-bound API calls these are equivalent in throughput, and FastAPI (W3) wraps sync handlers in a threadpool transparently, so we don't need to rewrite to asyncio.
- `ai/cache_manager.py` provides a file-based sha256 cache. Sufficient until W2 swaps it for Postgres-backed.
- `requirements.txt` exists with a minimal manifest (no torch/CUDA bloat).
- The `vn/` Ren'Py module is gone — confirms the EPUB-to-VN sunset and removes the W5 reference to `vn/asset_pipeline.py`.

W1 done:
- `pipeline/` package added (`analyze.py`, `characters.py`, `scenes.py`, `illustrate.py`); `book_to_vn.py` now calls `pipeline.X.run(...)` directly instead of shelling out via `subprocess.run`. Standalone CLI scripts kept for debugging.
- `ai/llm_providers.py` SIGALRM machinery removed; Bedrock client now built with `botocore.Config(connect_timeout=15, read_timeout=60, retries=standard/3)`. Safe inside threadpool workers.
- Multi-image conditioning in `ai/consistent_scene_generator.py` verified: `ai/gemini_image_generator.py:191-206` builds `contents=[PIL.Image, ..., prompt]` and passes it through `client.models.generate_content(contents=...)`. Photo-of-kid in W4 has a working code path.

## First steps on a fresh checkout

```bash
uv venv --python 3.14 .venv          # 3.13 EOL'd; matches what most distros now ship
uv pip install -r requirements.txt
cp .env.example .env  # if added; otherwise create with GEMINI_API_KEY + GEMINI_MODEL + AWS creds
```

The host I last worked on had a `.venv` that was created on 3.13 then orphaned by a system Python upgrade to 3.14. Recreating with `uv venv --python 3.14` and reinstalling from `requirements.txt` resolves it cleanly in ~2 minutes.

## Workstreams (sequenced)

### W0 · Naming + domain · day 1 · non-blocking
Pick a name, register the domain, set up Vercel + Supabase + Stripe + Inngest accounts. Reserve the trademark search. Throwaway logo via Recraft / SVG. **Blocker for launch, not for code.**

### W1 · Kill the subprocess chain · ✅ done

Landed:
- `pipeline/{analyze,characters,scenes,illustrate}.py` — thin in-process wrappers around the `ai/` classes; each exposes `run(...)`.
- `book_to_vn.py` — four `subprocess.run` calls replaced with `pipeline.X.run(...)` imports.
- `ai/llm_providers.py` — SIGALRM removed; Bedrock client uses `botocore.Config(connect_timeout=15, read_timeout=60, retries=standard/3)`.
- Gemini multi-image conditioning verified at `ai/gemini_image_generator.py:191-206`.

Deferred (small follow-ups, none blocking W2/W3):
- `pipeline/orchestrator.py` (a single `run_book(...)` entry point) — `book_to_vn.py` is still the orchestrator. The FastAPI worker in W3 can call into the same four stage modules without it; if the worker grows enough to want a single entry point, lift one out then.
- `pipeline/backgrounds.py` — `generate_environment_images.py` is not called by `book_to_vn.py` today; wrap if/when needed.
- Honest end-to-end baseline timing on `books/alice.epub --chapters demo` — needs `GEMINI_API_KEY` + AWS creds to be present; measure when next iterating on perf.

### W2 · Supabase: Postgres + Storage + Auth · ~4 days

Goal: kill `books.json` and the `output/` + `frontend/public/data/` mirror. The mirror stays in place until W4 retires the CRA reader; W2 lands the Supabase write path as an *additive* second sink.

Landed:
- `db/schema.sql` — canonical declarative schema (`users`, `books`, `pages`, `jobs`, `purchases`) + RLS + private storage buckets (`book-images`, `child-photos`, `book-pdfs`) keyed `<user_id>/<book_id>/...`. Enums for status fields; updated_at triggers; auto-provisioning `public.users` row on `auth.users` insert. The `books` table includes `language` (default `'nb-NO'`).
- `supabase/migrations/20260513170000_initial.sql` — the actual migration the Supabase CLI applies (`supabase db push`). `db/schema.sql` stays as the human-readable snapshot; deltas land as additional `supabase/migrations/<timestamp>_*.sql` files going forward.
- Applied to the **drømmevev** project (`xfbuuzxxvjcgzumtymzu`, West EU Ireland) on 2026-05-13. `supabase migration list` confirms local & remote in sync.
- `pipeline/storage.py` — sync `SupabaseStore` (uses `service_role`), `upload_file` / `upload_directory` / `signed_url`, `upsert_book` / `upsert_pages`, plus a `push_book_artifacts(...)` helper that mirrors `_copy_to_react_app`. `from_env()` returns `None` when env vars are absent so callers no-op gracefully. A deterministic `book_id_from_slug()` keeps CLI re-runs idempotent.
- `book_to_vn.py` — new `sync` step (step 8) at the end of the pipeline; `--resume-from sync` available. Logs and skips when `SUPABASE_URL` is unset.
- `requirements.txt` adds `supabase`; `.env.example` documents `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`.

Smoke-tested 2026-05-13 against `output/alice/`: 25 image assets land under `book-images/<dev_user>/<book_id>/{characters,scenes}/`, 30 page rows in `pages`, 1 row in `books` with `status='ready'`. The CLI lazily provisions a `dev@drommevev.local` auth user on first run via the admin API.

Not yet done:
- Replace `backend/api.py` — kept for now since the CRA reader still calls it; deletion happens in W4 when the Next.js viewer lands.
- Postgres-backed cache promotion (the file-based `ai/cache_manager.py` works for CLI; the worker in W3 can swap to a `prompts` table if the cache hit rate proves load-bearing).
- Surface Supabase signed-URL retrieval from the React app — also a W4 concern.

### W3 · FastAPI worker + Inngest orchestration · ~4 days
Wrap the `pipeline/` stages behind a FastAPI service deployed on Fly.io. Inngest defines the durable workflow; the Python SDK is mounted directly inside FastAPI so the worker process *is* the executor — no separate Next.js handler needed for W3.

Landed (skeleton only — stage logic stubs):
- `worker/main.py` — FastAPI app, `GET /healthz`, mounts `inngest.fast_api.serve(...)` at `/api/inngest`.
- `worker/jobs.py` — `inngest.Inngest(app_id="drommevev-worker")` + `book_generate` function triggered on `book.generate`, with six `step.run(...)` boundaries (`load-book`, `mark-generating`, `analyze`, `characters`, `scenes`, `illustrate`, `mark-ready`). Reads/writes Supabase via service_role. `retries=2`.
- `worker/Dockerfile` — `python:3.14-slim`, copies `ai/ + pipeline/ + worker/`, installs `requirements.txt`, `uvicorn worker.main:app` on port 8000.
- `worker/fly.toml` — Amsterdam region (`ams`), `shared-cpu-1x`/1GB, auto-stop machines (Inngest webhooks wake on demand).
- `requirements.txt` adds `fastapi`, `uvicorn[standard]`, `inngest`.

Smoke-tested locally 2026-05-13: `uvicorn worker.main:app` + `npx inngest-cli@latest dev`, registration sync succeeds, `POST /e/test` with `{"name":"book.generate","data":{"book_id":"<alice uuid>"}}` runs to `Completed` in 1.5s and flips `books.status` from `ready` → `generating` → `ready` (the stub stages no-op between the two marks).

Not yet done (gated on input flows in W4):
- Wire each stub `step.run` to its real `pipeline/` stage. Today `pipeline.analyze.run` etc. expect an EPUB path; the W4 write/guided/photo/drawing flows produce different inputs that need their own pipeline entry points.
- Deploy: `fly launch --copy-config --config worker/fly.toml --dockerfile worker/Dockerfile --no-deploy`, then `fly secrets set ...` (Supabase + Gemini + Inngest keys), then `fly deploy`. Not done yet — waiting on explicit go-ahead.
- Once deployed, swap `inngest.Inngest(...)` to production mode (`INNGEST_ENV=production`) and point Inngest Cloud at the Fly URL.

**Critical files (W4-facing)**:
- `app/api/inngest/route.ts` — Next.js handler that sends events via `inngest.send(...)`. Defer until W4.
- `lib/inngest/functions/generate-book.ts` — not needed; the Python worker owns the function definition. Next.js only enqueues.

### W4 · Frontend: Next.js + 4 creation flows + viewer · ~10 days
Bootstrap a fresh Next.js app in `web/` (don't try to retrofit `frontend/`). Migrate the *idea* of `BookReader`/`ImagePanel`/`TextPanel` (`frontend/src/components/`) but rewrite as RSC + client islands — the existing components are tightly coupled to local fetch paths.

Landed (scaffolding only):
- `web/` — Next.js 16 + App Router + TypeScript + Tailwind v4 + Turbopack. `lang="nb-NO"` on `<html>`. EB Garamond serif + Inter sans wired via `next/font`. Tailwind `@theme` carries the Drømmevev palette (surface `#FAF9F6`, primary `#E67E22`, sage/sky/marigold accents).
- `web/src/lib/supabase/{server,browser}.ts` — `@supabase/ssr` wrappers reading `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` from `.env.local` (gitignored).
- `web/src/app/page.tsx` — Norwegian landing page with brand wordmark, hero copy, "Lag en bok sammen" CTA, three-step workshop method, footer "Drømmevev fra aiakaki · © 2026".
- `package-lock.json` at repo root removed (vestigial empty stub that confused Turbopack's workspace-root detection).

Smoke-tested 2026-05-13: `npm run dev -- --port 3010` renders `/` with 200 OK, Norwegian copy in HTML.

Routes:
- `/` — landing (hero, sample books, CTA)
- `/create` — input mode picker (4 cards)
- `/create/write` — type/dictate flow (uses Web Speech API for dictation)
- `/create/guided` — step-form: hero/setting/problem/lesson → generate
- `/create/photo` — Supabase Storage upload + likeness consent + style picker
- `/create/drawing` — drawing upload + style-transfer instruction
- `/book/[id]` — viewer with progress (skeleton pages → fade in as Inngest fans out)
- `/book/[id]/download` — gated by purchase, hits PDF endpoint
- `/library` — user's books
- `/account` — credits, purchase history

**Components to port (from `frontend/src/components/`)**:
- `BookReader.tsx` → `web/components/BookViewer.tsx` (RSC shell + client carousel)
- `ImagePanel.tsx` → `web/components/PageSpread.tsx`
- `Navigation.tsx` → page nav (use `next/navigation`)
- `BookChooser.tsx` → `/library` page

The four input flows feed into the **same backend pipeline** — they just pre-fill the prompt differently. The kid-photo flow adds a `child_photo_url` that gets passed to Gemini as conditioning input via the (now-fixed in W1) multi-image-conditioning code path in `pipeline/illustrate.py`.

### W5 · PDF export · ~3 days
Two viable approaches; pick one:

**Approach A: Pillow + reportlab (recommended)** — `pipeline/pdf.py` builds an A4 layout from scratch (the old `vn/asset_pipeline.py` PIL helper was deleted upstream). One page per book page: full-bleed image + caption text in a serif font. Renders in 1-2s server-side. Pre-render at purchase time, store in Storage.

**Approach B: Playwright HTML→PDF** — better typography, but requires Chromium in the worker container (~300MB image). Skip unless A produces ugly output.

**Critical files**:
- `pipeline/pdf.py` (new — uses Pillow + `reportlab` for text layout)
- `worker/main.py` adds `POST /jobs/render-pdf`

### W6 · Stripe + paywall · ~3 days
- Stripe Products: "1 book — $19", "3 books — $39", "10 books — $99".
- Checkout Sessions from `/account/buy`. Webhook (`/api/stripe/webhook`) credits user.
- Server enforces credit decrement on book creation (`pipeline/orchestrator.py` first action).
- Free tier: 1 watermarked preview book per account. Paywall = remove watermark + unlock PDF download.

### W7 · Safety + compliance · ~3 days
This is the **single biggest non-engineering risk** for a "upload your kid's photo" product.

- **COPPA posture**: parent creates the account; clear ToS that no account is for under-13s, photos are uploaded by the parent on behalf of the child.
- **Photo handling**: private bucket, never indexed, deleted on account deletion, never used to train any model. Document this in plain English on `/create/photo`.
- **Likeness consent checkbox**: explicit, unticked by default, blocks submit.
- **NSFW filter on outputs**: Gemini already refuses, but add a Vision-API-backed second pass on every generated page before showing to user. Use Bedrock's Rekognition or a small local CLIP NSFW classifier.
- **Text moderation on inputs**: parent's prompt goes through `bedrock-runtime` Guardrails or OpenAI Moderation before story generation. Block the obvious stuff.
- **Refund policy** for failed generations: track `jobs.status='failed'` and auto-credit retry tokens.

### W8 · Marketing + analytics · ~3 days
- Landing page with 3 sample books rendered live (use the kids' nieces/nephews if applicable; otherwise commission 3).
- OG cards per published book (`/book/[id]/og` route, 1200x630, first page image + title).
- PostHog for funnel: `/create` → input mode → first page rendered → purchase. The drop-off between "first page rendered" and "purchase" is the revenue dial — instrument it day one.
- Plausible or simple PostHog dashboards for landing → signup.

## Files reused from the existing codebase (don't rewrite)

| Existing file | New role |
|---|---|
| `ai/character_image_prompter.py` | Powers guided + write flows; called from `pipeline/characters.py` |
| `ai/expression_prompter.py` | Per-page emotional variation |
| `ai/consistent_scene_generator.py` | Photo-of-kid conditioning; verify in W1 that ref images go through `contents=[...]` not just prompt text |
| `ai/scene_segmentation.py` | Splits parent's story into pages; already thread-parallel across chapters |
| `ai/gemini_image_generator.py` | Image gen; already thread-parallel via ThreadPoolExecutor |
| `ai/llm_providers.py` | LLM provider abstraction — fix SIGALRM timeout in W1 (crashes in threadpool workers) |
| `ai/cache_manager.py` | File-based sha256 cache; swap to Postgres-backed in W2 |
| `frontend/src/components/BookReader.tsx` | Port to `web/components/BookViewer.tsx` |

## Performance targets (be honest about these)

| Metric | Today | Target | Mechanism |
|---|---|---|---|
| Wall time, 10-page book | TBD (measure post-rebuild) | **15-25s** | ThreadPoolExecutor parallelism (already landed in `cbb7b0c`) |
| Time to first page visible to user | full pipeline | **<5s** | Stream pages to UI as they finish; skeleton placeholders (W3+W4) |
| Cost per book | ~$0.50 | ~$0.50 first gen, **~$0.05 on text edits** | `ai/cache_manager.py` (already landed); promoted to Postgres in W2 |
| Image payload size | unbounded PNG | **AVIF + responsive** | Next.js Image + Supabase Storage transforms (W4) |
| PDF render time | n/a | **<2s** | Pillow + reportlab server-side (W5) |
| p95 backend response (non-job routes) | n/a | **<200ms** | Postgres indexes + Vercel edge (W2+W4) |

## Decisions deferred (not blocking; surface during build)

1. **Brand name + domain** — needed before W4 ships, not before W1 starts.
2. **Exact pricing** — $19 single / $39 for 3 / $99 for 10 is a starting point; A/B once data exists.
3. **Free tier shape** — 1 free watermarked book vs. 1 free unwatermarked low-res preview. Recommend the latter; better conversion.
4. **Print-on-demand later?** — out of scope for v1; revisit at month 3 if PDF sells.
5. **EU AI Act / GDPR posture** — if user is in EU, the photo-of-kid path needs explicit GDPR DPA copy + EU-region Supabase project. Worth confirming before W7.

## Verification plan

End-to-end smoke test, run weekly during build and as the launch gate:

1. **Local dev**: `pnpm dev` (Next.js) + `uvicorn worker.main:app --reload` + `npx inngest-cli@latest dev` + Supabase local stack. One command via `Procfile` / `mprocs`.
2. **E2E flow** (Playwright):
   - Sign up → land in `/library`
   - Buy a 3-book pack via Stripe test card `4242 4242 4242 4242`
   - Create book via "guided" flow
   - Watch pages stream in (assert all 10 done < 30s)
   - Open viewer, scrub through pages
   - Click download → PDF arrives, opens, has 10 pages with images
3. **Photo flow regression**: upload a stock photo of a child (consented test asset), generate, manually inspect 3 pages — protagonist must be visually consistent across pages.
4. **Cost ceiling**: log every Bedrock + Gemini call to a `usage` table; assert `SUM(cost) per book < $0.80`.
5. **Pre-launch checklist**:
   - Stripe webhook idempotency tested (same event ×2 → 1 credit)
   - Supabase RLS audited (try to read another user's book → denied)
   - NSFW filter rejects a known-bad prompt
   - PDF passes a basic accessibility check (text layer present, not scanned image)
   - Domain SSL, OG cards, robots.txt, sitemap

## Open risks

- **Likeness quality from a single uploaded photo** is the make-or-break feature. Gemini 2.5 Flash Image is decent but not best-in-class. Budget 1 week of W4 for an honest evaluation: if it can't keep the kid recognizable across 10 pages, fall back to fal.ai Flux Kontext or Replicate's IP-Adapter. Don't ship a product that produces a different kid every page.
- **Inngest free tier** caps at 50K steps/month. With ~12 steps per book, that's ~4K books/mo before paid. Fine for MVP; price it at $20/book and we hit the ceiling at $80K MRR — at which point paying Inngest is trivial.
- **Print quality** — if customers print a 1024×1024 web image at 8×8" they'll see jaggies. PDF generation must request 2048×2048 from Gemini (more expensive but mandatory). Costed in.
- **One-person ops surface** — Stripe disputes, Supabase migrations, Fly.io scaling, customer support. Plan a weekly 4-hour "ops day" from launch.

## Suggested order of operations

```
Week 1   W0 (naming) ‖ W1 (kill subprocess chain — only ~2-3 days now) ‖ start W2 (Supabase)
Week 2   W2 (Supabase) finishes
Week 3   W3 (worker + Inngest)
Week 4   W4 part 1 (Next.js + auth + library + viewer)
Week 5   W4 part 2 (4 creation flows)
Week 6   W5 (PDF) ‖ W6 (Stripe)
Week 7   W7 (safety) ‖ W8 (marketing)
Week 8   Hardening, friend-and-family beta, launch
```

W1 must finish before W3 starts; W2 must finish before W3 and W4. Everything else can shuffle. With per-stage parallelism + cache already on `main`, W1 collapses from 5 days to ~2-3, freeing the saved time to start W2 in week 1.
