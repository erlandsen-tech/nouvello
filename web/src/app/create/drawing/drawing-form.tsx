"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

const LENGTHS = [
  { minutes: 2, label: "Kort", body: "~5 sider" },
  { minutes: 5, label: "Mellomlang", body: "~10 sider" },
  { minutes: 10, label: "Lang", body: "~15 sider" },
] as const;

type Minutes = (typeof LENGTHS)[number]["minutes"];

const MAX_BYTES = 8 * 1024 * 1024;
const MIN_PROMPT = 10;
const MAX_PROMPT = 280;

export function DrawingForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [title, setTitle] = useState("");
  const [minutes, setMinutes] = useState<Minutes>(5);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setError(null);
    if (!f) {
      setFile(null);
      setPreviewUrl(null);
      return;
    }
    if (!f.type.startsWith("image/")) {
      setError("Filen må være et bilde (JPG, PNG, HEIC).");
      return;
    }
    if (f.size > MAX_BYTES) {
      setError("Bildet er for stort — maks 8 MB.");
      return;
    }
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    const trimmed = prompt.trim();
    if (trimmed.length < MIN_PROMPT) {
      setError(`Skriv litt om hva tegningen handler om — minst ${MIN_PROMPT} tegn.`);
      return;
    }
    setError(null);

    startTransition(async () => {
      const supabase = createSupabaseBrowserClient();

      const { data: claimsData } = await supabase.auth.getClaims();
      if (!claimsData) {
        setError("Du er ikke lenger logget inn. Last siden på nytt.");
        return;
      }
      const userId = claimsData.claims.sub;

      const ext = file.name.split(".").pop()?.toLowerCase() || "jpg";
      const objectPath = `${userId}/${crypto.randomUUID()}.${ext}`;

      // child-photos bucket reused as the user-upload bucket for V1 — bucket
      // naming predates the drawing flow. Schema cleanup is deferred.
      const upload = await supabase.storage
        .from("child-photos")
        .upload(objectPath, file, {
          cacheControl: "3600",
          upsert: false,
          contentType: file.type,
        });

      if (upload.error) {
        console.error("[drawing-form] upload failed:", upload.error);
        setError(`Opplasting feilet: ${upload.error.message}`);
        return;
      }

      const res = await fetch("/api/books", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input_kind: "drawing",
          title: title.trim() || "Tegningens eventyr",
          input_payload: { prompt: trimmed, target_minutes: minutes },
          child_photo_url: objectPath,
        }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        console.error("[drawing-form] /api/books failed:", detail);
        setError(detail.error ?? "Kunne ikke starte boken.");
        return;
      }

      const { book_id } = (await res.json()) as { book_id: string };
      router.push(`/book/${book_id}`);
    });
  }

  const canSubmit = Boolean(
    file && prompt.trim().length >= MIN_PROMPT && !pending,
  );

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-8">
      <FileUpload
        file={file}
        previewUrl={previewUrl}
        onChange={handleFileChange}
        disabled={pending}
      />

      <label className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between">
          <span className="font-sans text-sm uppercase tracking-[0.16em] text-[color:var(--color-ink-soft)]">
            Hva handler tegningen om?
          </span>
          <span className="font-sans text-xs text-[color:var(--color-ink-soft)]">
            {prompt.length} / {MAX_PROMPT}
          </span>
        </div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value.slice(0, MAX_PROMPT))}
          placeholder="En drage som er redd for ild …"
          rows={3}
          disabled={pending}
          className="rounded-xl border border-black/10 bg-white/80 px-4 py-3 font-serif text-base leading-relaxed outline-none focus:border-[color:var(--color-primary)] focus:ring-2 focus:ring-[color:var(--color-primary)]/30"
        />
      </label>

      <label className="flex flex-col gap-2">
        <span className="font-sans text-sm uppercase tracking-[0.16em] text-[color:var(--color-ink-soft)]">
          Tittel <span className="normal-case opacity-60">(valgfritt)</span>
        </span>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Den modige dragen"
          maxLength={80}
          disabled={pending}
          className="rounded-xl border border-black/10 bg-white/80 px-4 py-3 font-sans text-base outline-none focus:border-[color:var(--color-primary)] focus:ring-2 focus:ring-[color:var(--color-primary)]/30"
        />
      </label>

      <fieldset className="flex flex-col gap-3">
        <legend className="font-sans text-sm uppercase tracking-[0.16em] text-[color:var(--color-ink-soft)]">
          Lesetid
        </legend>
        <div className="grid gap-3 sm:grid-cols-3">
          {LENGTHS.map((opt) => (
            <label
              key={opt.minutes}
              className={`cursor-pointer rounded-2xl border p-4 text-left transition ${
                minutes === opt.minutes
                  ? "border-[color:var(--color-primary)] bg-white shadow-sm"
                  : "border-black/10 bg-white/60 hover:border-black/20"
              }`}
            >
              <input
                type="radio"
                name="minutes"
                value={opt.minutes}
                checked={minutes === opt.minutes}
                onChange={() => setMinutes(opt.minutes)}
                className="sr-only"
                disabled={pending}
              />
              <div className="flex items-baseline gap-2">
                <span className="font-serif text-2xl">{opt.minutes}</span>
                <span className="font-sans text-xs uppercase tracking-[0.14em] text-[color:var(--color-ink-soft)]">
                  min
                </span>
              </div>
              <span className="mt-1 block font-serif text-base">{opt.label}</span>
              <span className="mt-1 block font-sans text-sm text-[color:var(--color-ink-soft)]">
                {opt.body}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {error ? (
        <p className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 font-sans text-sm text-red-800">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={!canSubmit}
        className="inline-flex items-center justify-center rounded-full bg-[color:var(--color-primary)] px-8 py-4 font-sans text-base font-medium text-[color:var(--color-primary-ink)] shadow-sm transition hover:brightness-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-primary)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--color-surface)] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {pending ? "Veving av eventyret …" : "Lag boken"}
      </button>
    </form>
  );
}

function FileUpload({
  file,
  previewUrl,
  onChange,
  disabled,
}: {
  file: File | null;
  previewUrl: string | null;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  disabled: boolean;
}) {
  return (
    <label
      className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-black/15 bg-white/60 p-8 text-center transition hover:border-[color:var(--color-primary)] hover:bg-white ${
        disabled ? "pointer-events-none opacity-60" : ""
      }`}
    >
      <input
        type="file"
        accept="image/*"
        onChange={onChange}
        className="sr-only"
        disabled={disabled}
      />
      {previewUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={previewUrl}
          alt={file?.name ?? "Forhåndsvisning"}
          className="h-48 w-48 rounded-xl object-cover shadow-sm"
        />
      ) : (
        <div className="flex h-48 w-48 items-center justify-center rounded-xl bg-[color:var(--color-sky)]/30 font-serif text-5xl text-[color:var(--color-ink-soft)]">
          +
        </div>
      )}
      <span className="font-sans text-sm text-[color:var(--color-ink-soft)]">
        {file ? file.name : "Trykk for å velge en tegning"}
      </span>
      <span className="font-sans text-xs text-[color:var(--color-ink-soft)]/70">
        JPG, PNG eller HEIC. Maks 8 MB.
      </span>
    </label>
  );
}
