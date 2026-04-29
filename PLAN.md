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

## First steps on a fresh checkout

Before any of the workstreams below can run, the host needs a working Python env. The original `.venv` had no manifest (the README referred to "the venv IS the manifest") which broke the moment the OS upgraded Python. **Don't repeat that mistake** — start by writing a real `requirements.txt`.

```bash
# Minimal direct deps (the existing site-packages had ~6GB of torch/CUDA + transformers
# + nltk + sklearn + scipy that are not imported anywhere in the codebase — skip them).
cat > requirements.txt <<'EOF'
google-genai>=1.0
boto3>=1.40
ebooklib>=0.19
beautifulsoup4>=4.12
lxml>=5.0
python-dotenv>=1.0
pillow>=10.0
fastapi>=0.115
uvicorn[standard]>=0.30
httpx>=0.27
pytest>=8.0
pytest-asyncio>=0.24
EOF

uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# Sanity-check
.venv/bin/python -c "from google import genai; print(dir(genai.Client(api_key='x').aio.models))"

# Re-create .env (gitignored). The previous key was rotated.
cat > .env <<'EOF'
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash-image
AWS_REGION=eu-central-1
EOF
```

The pre-rebuild venv contained ~95 packages but only ~12 are actually imported. Audit any new dep before adding it; the worker container will be deployed and every MB matters on cold start.

## Workstreams (sequenced)

### W0 · Naming + domain · day 1 · non-blocking
Pick a name, register the domain, set up Vercel + Supabase + Stripe + Inngest accounts. Reserve the trademark search. Throwaway logo via Recraft / SVG. **Blocker for launch, not for code.**

### W1 · Refactor pipeline: subprocess → async library · ~5 days
The single biggest performance win. Today: `book_to_vn.py` shells out to seven scripts; each script then calls Gemini sequentially for ~10 images. Wall time per book: 90-120s.

- Promote each script's `main()` body into an importable function in a new `pipeline/` package. `analyze_chapters.py`, `generate_character_images.py`, `ai/scene_segmentation.py`, `ai/consistent_scene_generator.py`, `generate_environment_images.py` all collapse into `pipeline/{analyze,characters,scenes,illustrate,backgrounds}.py`.
- Replace the per-step `subprocess.run` calls in `book_to_vn.py` with direct awaits.
- Make `GeminiImageGenerator` async (`google-genai` already supports `aio.models.generate_content`). Use `asyncio.Semaphore(5)` to respect rate limits while parallelizing the 10 page renders.
- Expected wall time: **15-25s** for a 10-page book (5x-7x speedup).
- Add a content-hash cache layer: `sha256(input_text + character_seed + page_idx)` → previously rendered image URL in Postgres. Iteration cost on text edits drops from $0.50 → ~$0.05.
- **Bug to fix while you're in here**: `ai/consistent_scene_generator.py:152-158` claims to use character reference images for consistency but only passes them in the *text* of the prompt — never as actual `contents` to the Gemini API. The photo-of-kid feature (W4) hard-depends on real multi-image conditioning, so this gets fixed in W1. The `google.genai` SDK accepts `contents=[prompt, PIL.Image, PIL.Image, ...]` directly.

**Critical files to create / modify**:
- `pipeline/__init__.py`, `pipeline/orchestrator.py` (new — replaces `book_to_vn.py`'s flow)
- `pipeline/illustrate.py` (refactor of `ai/consistent_scene_generator.py:39` into async)
- `ai/gemini_image_generator.py` (add async client; keep sync entry points for backward-compat with `generate_environment_images.py` until W3)
- `ai/llm_providers.py:33` (add `async def generate_response`; replace `signal.SIGALRM` timeout — line ~107 — with `asyncio.wait_for`, the SIGALRM approach hard-fails in any non-main-thread or async context)
- `pipeline/cache.py` (new — content-hash cache; FS-backed in W1, swapped to Postgres in W2)

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

**Approach A: Pillow-based (recommended)** — extend `vn/asset_pipeline.py:11` (already does `PIL.Image` + `RGBA` + resize) with a layout step. One A4 page per book page: full-bleed image + caption text in a serif font. Renders in 1-2s server-side. Pre-render at purchase time, store in Storage.

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
| `ai/consistent_scene_generator.py:39` | Photo-of-kid conditioning (existing multi-image input path; bug fix in W1) |
| `ai/scene_segmentation.py:37` | Splits parent's story into pages |
| `ai/gemini_image_generator.py` | Image gen — needs async wrapper |
| `ai/llm_providers.py:33` | LLM provider abstraction — add async + content moderation; remove SIGALRM timeout |
| `vn/asset_pipeline.py:11` | PIL utilities → reused in `pipeline/pdf.py` |
| `frontend/src/components/BookReader.tsx` | Port to `web/components/BookViewer.tsx` |

## Performance targets (be honest about these)

| Metric | Today | Target | Mechanism |
|---|---|---|---|
| Wall time, 10-page book | 90-120s | **15-25s** | Async Gemini + `asyncio.gather` with semaphore (W1) |
| Time to first page visible to user | 90-120s | **<5s** | Stream pages to UI as they finish; skeleton placeholders (W3+W4) |
| Cost per book | ~$0.50 | ~$0.50 first gen, **~$0.05 on text edits** | Content-hash cache (W1) |
| Image payload size | unbounded PNG | **AVIF + responsive** | Next.js Image + Supabase Storage transforms (W4) |
| PDF render time | n/a | **<2s** | Pillow server-side (W5) |
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
Week 1   W0 (naming) ‖ W1 (async refactor)
Week 2   W2 (Supabase)
Week 3   W3 (worker + Inngest)
Week 4   W4 part 1 (Next.js + auth + library + viewer)
Week 5   W4 part 2 (4 creation flows)
Week 6   W5 (PDF) ‖ W6 (Stripe)
Week 7   W7 (safety) ‖ W8 (marketing)
Week 8   Hardening, friend-and-family beta, launch
```

W1 must finish before W3 starts; W2 must finish before W3 and W4. Everything else can shuffle.
