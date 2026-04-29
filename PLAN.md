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

What's still untouched from W1:
- `book_to_vn.py` still shells out to seven scripts via `subprocess.run` (lines 261, 312, 359, 596). For a deployed worker we need this in-process so a single function call runs the whole pipeline.
- `ai/llm_providers.py` still uses `signal.SIGALRM` for Bedrock timeouts — that crashes inside any ThreadPoolExecutor worker (which is now the default). Replace with `botocore.Config(connect_timeout=..., read_timeout=...)`.
- `ai/consistent_scene_generator.py` claims to use character reference images as conditioning but historically only passed them in the text prompt; verify post-refactor and fix if still wrong (photo-of-kid in W4 hard-depends on real multi-image input).

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

### W1 · Kill the subprocess chain · ~2-3 days (down from 5)
Per-stage parallelism and caching already landed on `main`. What remains is the orchestrator: `book_to_vn.py` still shells out to four separate Python processes, which means the worker (W3) can't run a book end-to-end inside a single FastAPI handler.

- Promote each script's `main()` body into an importable `run(...)` function in a new `pipeline/` package. `analyze_chapters.py`, `generate_character_images.py`, `ai/scene_segmentation.py`, `ai/consistent_scene_generator.py`, `generate_environment_images.py` all expose `run(...)` callables that `pipeline/orchestrator.py` imports and calls directly.
- Replace the four `subprocess.run` calls in `book_to_vn.py` (lines ~261, 312, 359, 596) with direct in-process function calls. Keep the CLI as a thin wrapper that calls `pipeline.orchestrator.run_book(...)`.
- Fix `ai/llm_providers.py` SIGALRM timeout — it crashes inside any ThreadPoolExecutor worker, which is now the default. Replace with `botocore.Config(connect_timeout=15, read_timeout=60)` and built-in retries.
- Verify `ai/consistent_scene_generator.py` actually passes character reference images via `contents=[prompt, PIL.Image, ...]` to Gemini, not just in the prompt text. Photo-of-kid in W4 fails silently if this is wrong.
- Establish an honest baseline once the venv is rebuilt: time `book_to_vn.py books/alice.epub --chapters demo` end-to-end. The plan's earlier "90-120s" claim predates the threading commit; the real number is unknown until measured.

**Critical files to create / modify**:
- `pipeline/__init__.py`, `pipeline/orchestrator.py` (new — replaces `book_to_vn.py`'s subprocess flow)
- `pipeline/{analyze,characters,scenes,illustrate,backgrounds}.py` (thin wrappers around existing `ai/` modules)
- `ai/llm_providers.py` (drop SIGALRM, use botocore.Config)
- `ai/consistent_scene_generator.py` (verify multi-image conditioning; fix if missing)

### W2 · Supabase: Postgres + Storage + Auth · ~4 days
Kill `books.json` and the `output/` + `frontend/public/data/` mirror.

Schema (start small, grow):
```sql
users          (id, email, created_at, stripe_customer_id, credits_remaining)
books          (id, user_id, title, status, input_kind, child_photo_url, created_at)
pages          (id, book_id, page_idx, text, image_url, image_status, prompt_hash)
jobs           (id, book_id, kind, status, error, started_at, finished_at)
purchases      (id, user_id, stripe_session_id, credits_added, amount_cents)
```
RLS: users can only read their own rows. Storage buckets: `book-images/<user_id>/<book_id>/...`, `child-photos/<user_id>/...` (private, signed URLs only).

**Critical files to touch**:
- `backend/api.py` → delete (replaced by Next.js routes + FastAPI worker)
- New `db/schema.sql` and `db/migrations/`
- New `pipeline/storage.py` to upload PNGs/PDFs into Supabase Storage instead of `frontend/public/`

### W3 · FastAPI worker + Inngest orchestration · ~4 days
Wrap `pipeline/orchestrator.py` in a FastAPI service deployed on Fly.io (cheaper than Render for always-on workers; `.venv` deps just work).

- `POST /jobs/generate-book` accepts `{book_id}`, looks up the book, runs the pipeline, writes pages to Postgres + Storage as they finish.
- Inngest function `book.generate` calls this endpoint with retry + step durability. One Inngest step per stage so retries are cheap.
- Frontend gets progress via Supabase realtime on the `pages` table (image_status: `pending → generating → done`).

**Critical files to create**:
- `worker/main.py` (FastAPI app)
- `worker/Dockerfile` (Python 3.14, copies `ai/` + `pipeline/`, installs from `requirements.txt`)
- `worker/fly.toml`
- `app/api/inngest/route.ts` (Next.js Inngest handler)
- `lib/inngest/functions/generate-book.ts`

### W4 · Frontend: Next.js + 4 creation flows + viewer · ~10 days
Bootstrap a fresh Next.js 15 app in `web/` (don't try to retrofit `frontend/`). Migrate the *idea* of `BookReader`/`ImagePanel`/`TextPanel` (`frontend/src/components/`) but rewrite as RSC + client islands — the existing components are tightly coupled to local fetch paths.

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
