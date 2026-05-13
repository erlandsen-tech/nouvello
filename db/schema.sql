-- Canonical declarative schema for the picture-book product (PLAN.md W2).
-- Run against a fresh Supabase project, then keep incremental changes in db/migrations/.
-- Run order: extensions → tables → indexes → RLS policies → storage buckets → triggers.

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
create extension if not exists pgcrypto;            -- gen_random_uuid()
create extension if not exists "uuid-ossp";

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

-- Per-parent profile, keyed off Supabase Auth's auth.users.
-- We call it "users" to match PLAN.md; queries should qualify as public.users.
create table if not exists public.users (
    id                   uuid primary key references auth.users(id) on delete cascade,
    email                text not null,
    stripe_customer_id   text unique,
    credits_remaining    integer not null default 0 check (credits_remaining >= 0),
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now()
);

create type public.book_status as enum (
    'draft',         -- input captured, not yet queued
    'queued',        -- handed off to Inngest / worker
    'generating',    -- worker actively producing pages
    'ready',         -- all pages rendered
    'failed',        -- terminal failure
    'archived'       -- soft-deleted
);

create type public.book_input_kind as enum (
    'write',         -- typed/dictated story
    'guided',        -- step-form prompt
    'photo',         -- hero photo
    'drawing'        -- kid's drawing
);

create table if not exists public.books (
    id                  uuid primary key default gen_random_uuid(),
    user_id             uuid not null references public.users(id) on delete cascade,
    title               text not null default 'Untitled',
    status              public.book_status not null default 'draft',
    input_kind          public.book_input_kind not null,
    input_payload       jsonb not null default '{}'::jsonb,    -- raw flow inputs (prompt, guided answers, etc.)
    language            text not null default 'nb-NO',         -- BCP-47; drives LLM/image prompts. Norwegian-first product.
    child_photo_url     text,                                  -- storage path under child-photos/<user_id>/
    art_style           text,
    pdf_url             text,                                  -- storage path under book-pdfs/<user_id>/<book_id>/
    page_count          integer not null default 0,
    error               text,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

create index if not exists books_user_id_idx          on public.books(user_id);
create index if not exists books_status_idx           on public.books(status);
create index if not exists books_user_created_at_idx  on public.books(user_id, created_at desc);

create type public.page_status as enum (
    'pending',
    'generating',
    'done',
    'failed'
);

create table if not exists public.pages (
    id            uuid primary key default gen_random_uuid(),
    book_id       uuid not null references public.books(id) on delete cascade,
    page_idx      integer not null check (page_idx >= 0),
    text          text not null default '',
    image_url     text,                                       -- storage path under book-images/<user_id>/<book_id>/
    image_status  public.page_status not null default 'pending',
    prompt_hash   text,                                       -- sha256 of the image prompt for cache reuse
    error         text,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now(),
    unique (book_id, page_idx)
);

create index if not exists pages_book_id_idx           on public.pages(book_id);
create index if not exists pages_book_status_idx       on public.pages(book_id, image_status);

create type public.job_kind as enum (
    'analyze',
    'characters',
    'scenes',
    'illustrate',
    'render-pdf'
);

create type public.job_status as enum (
    'queued',
    'running',
    'succeeded',
    'failed'
);

create table if not exists public.jobs (
    id            uuid primary key default gen_random_uuid(),
    book_id       uuid not null references public.books(id) on delete cascade,
    kind          public.job_kind not null,
    status        public.job_status not null default 'queued',
    inngest_run_id text,
    error         text,
    started_at    timestamptz,
    finished_at   timestamptz,
    created_at    timestamptz not null default now()
);

create index if not exists jobs_book_id_idx   on public.jobs(book_id);
create index if not exists jobs_status_idx    on public.jobs(status);

create table if not exists public.purchases (
    id                   uuid primary key default gen_random_uuid(),
    user_id              uuid not null references public.users(id) on delete restrict,
    stripe_session_id    text not null unique,
    credits_added        integer not null check (credits_added > 0),
    amount_cents         integer not null check (amount_cents >= 0),
    currency             text not null default 'usd',
    created_at           timestamptz not null default now()
);

create index if not exists purchases_user_id_idx on public.purchases(user_id);

-- ---------------------------------------------------------------------------
-- updated_at maintenance
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists users_set_updated_at on public.users;
create trigger users_set_updated_at
    before update on public.users
    for each row execute function public.set_updated_at();

drop trigger if exists books_set_updated_at on public.books;
create trigger books_set_updated_at
    before update on public.books
    for each row execute function public.set_updated_at();

drop trigger if exists pages_set_updated_at on public.pages;
create trigger pages_set_updated_at
    before update on public.pages
    for each row execute function public.set_updated_at();

-- Auto-provision a public.users row whenever a new auth.users row is created.
create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.users (id, email)
    values (new.id, coalesce(new.email, ''))
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_auth_user();

-- ---------------------------------------------------------------------------
-- Row Level Security
--   - anon role:           no access
--   - authenticated role:  read+write own rows only
--   - service_role:        unrestricted (used by worker + webhooks)
-- ---------------------------------------------------------------------------

alter table public.users     enable row level security;
alter table public.books     enable row level security;
alter table public.pages     enable row level security;
alter table public.jobs      enable row level security;
alter table public.purchases enable row level security;

-- users: read/update own row
drop policy if exists users_self_select on public.users;
create policy users_self_select on public.users
    for select using (auth.uid() = id);

drop policy if exists users_self_update on public.users;
create policy users_self_update on public.users
    for update using (auth.uid() = id)
    with check (auth.uid() = id);

-- books: full CRUD on own rows
drop policy if exists books_owner_select on public.books;
create policy books_owner_select on public.books
    for select using (auth.uid() = user_id);

drop policy if exists books_owner_insert on public.books;
create policy books_owner_insert on public.books
    for insert with check (auth.uid() = user_id);

drop policy if exists books_owner_update on public.books;
create policy books_owner_update on public.books
    for update using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists books_owner_delete on public.books;
create policy books_owner_delete on public.books
    for delete using (auth.uid() = user_id);

-- pages: read own (via book.user_id); writes are worker-only via service_role
drop policy if exists pages_owner_select on public.pages;
create policy pages_owner_select on public.pages
    for select using (
        exists (
            select 1 from public.books b
            where b.id = pages.book_id and b.user_id = auth.uid()
        )
    );

-- jobs: same as pages
drop policy if exists jobs_owner_select on public.jobs;
create policy jobs_owner_select on public.jobs
    for select using (
        exists (
            select 1 from public.books b
            where b.id = jobs.book_id and b.user_id = auth.uid()
        )
    );

-- purchases: read own; written by Stripe webhook via service_role
drop policy if exists purchases_owner_select on public.purchases;
create policy purchases_owner_select on public.purchases
    for select using (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- Storage buckets (private; access via signed URLs only)
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('book-images', 'book-images', false)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('child-photos', 'child-photos', false)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('book-pdfs', 'book-pdfs', false)
on conflict (id) do nothing;

-- Objects are keyed as <user_id>/<book_id>/<filename>. RLS gates by the first path segment.
drop policy if exists storage_owner_select on storage.objects;
create policy storage_owner_select on storage.objects
    for select using (
        bucket_id in ('book-images', 'child-photos', 'book-pdfs')
        and (storage.foldername(name))[1] = auth.uid()::text
    );

drop policy if exists storage_owner_insert on storage.objects;
create policy storage_owner_insert on storage.objects
    for insert with check (
        bucket_id in ('book-images', 'child-photos', 'book-pdfs')
        and (storage.foldername(name))[1] = auth.uid()::text
    );

drop policy if exists storage_owner_delete on storage.objects;
create policy storage_owner_delete on storage.objects
    for delete using (
        bucket_id in ('book-images', 'child-photos', 'book-pdfs')
        and (storage.foldername(name))[1] = auth.uid()::text
    );
