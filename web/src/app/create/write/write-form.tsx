"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

const MIN_CHARS = 80;
const MAX_CHARS = 4000;

const LENGTHS = [
  { minutes: 2, label: "Kort", body: "~5 sider, perfekt på trøtte kvelder" },
  { minutes: 5, label: "Mellomlang", body: "~10 sider, en hel godnatt-stund" },
  { minutes: 10, label: "Lang", body: "~15 sider, for de som vil utsette sengen" },
] as const;

type Minutes = (typeof LENGTHS)[number]["minutes"];

export function WriteForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [minutes, setMinutes] = useState<Minutes>(5);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = text.trim();
    if (trimmed.length < MIN_CHARS) {
      setError(`Historien må være minst ${MIN_CHARS} tegn — gi oss litt mer å jobbe med.`);
      return;
    }
    setError(null);

    startTransition(async () => {
      const res = await fetch("/api/books", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input_kind: "write",
          title: title.trim() || "Eventyret",
          input_payload: { text: trimmed, target_minutes: minutes },
        }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        console.error("[write-form] /api/books failed:", detail);
        setError(detail.error ?? "Kunne ikke starte boken.");
        return;
      }

      const { book_id } = (await res.json()) as { book_id: string };
      router.push(`/book/${book_id}`);
    });
  }

  const remaining = MAX_CHARS - text.length;
  const tooLong = remaining < 0;
  const canSubmit = !pending && text.trim().length >= MIN_CHARS && !tooLong;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
      <label className="flex flex-col gap-2">
        <span className="font-sans text-sm uppercase tracking-[0.16em] text-[color:var(--color-ink-soft)]">
          Tittel <span className="normal-case opacity-60">(valgfritt)</span>
        </span>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Da månen kom på besøk"
          maxLength={80}
          disabled={pending}
          className="rounded-xl border border-black/10 bg-white/80 px-4 py-3 font-sans text-base outline-none focus:border-[color:var(--color-primary)] focus:ring-2 focus:ring-[color:var(--color-primary)]/30"
        />
      </label>

      <label className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between">
          <span className="font-sans text-sm uppercase tracking-[0.16em] text-[color:var(--color-ink-soft)]">
            Historien
          </span>
          <span className="font-sans text-xs text-[color:var(--color-ink-soft)]">
            Minst {MIN_CHARS} tegn
          </span>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Det var en gang en jente som ikke fikk sove …"
          rows={14}
          disabled={pending}
          className="rounded-xl border border-black/10 bg-white/80 px-4 py-4 font-serif text-lg leading-relaxed outline-none focus:border-[color:var(--color-primary)] focus:ring-2 focus:ring-[color:var(--color-primary)]/30"
        />
        <span
          className={`text-right font-sans text-xs ${
            tooLong
              ? "text-red-700"
              : "text-[color:var(--color-ink-soft)]"
          }`}
        >
          {tooLong
            ? `${Math.abs(remaining)} tegn for mye`
            : `${text.length} / ${MAX_CHARS} tegn`}
        </span>
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
