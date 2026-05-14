"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

const STYLES = [
  {
    id: "skisse",
    label: "Skisse",
    body: "Mykt blyant-aktig, lyse pasteller.",
  },
  {
    id: "akvarell",
    label: "Akvarell",
    body: "Drømmende vannfarger, bløte kanter.",
  },
  {
    id: "livlig",
    label: "Livlig",
    body: "Sterke farger, varm bildeboks-stemning.",
  },
] as const;

const MAX_BYTES = 8 * 1024 * 1024;

export function PhotoForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [style, setStyle] = useState<(typeof STYLES)[number]["id"]>("akvarell");
  const [consent, setConsent] = useState(false);
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
    if (!file || !consent) return;
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

      const upload = await supabase.storage
        .from("child-photos")
        .upload(objectPath, file, {
          cacheControl: "3600",
          upsert: false,
          contentType: file.type,
        });

      if (upload.error) {
        console.error("[photo-form] upload failed:", upload.error);
        setError(`Opplasting feilet: ${upload.error.message}`);
        return;
      }

      const res = await fetch("/api/books", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input_kind: "photo",
          title: title.trim() || "Eventyret om helten",
          input_payload: { style },
          child_photo_url: objectPath,
          art_style: style,
        }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        console.error("[photo-form] /api/books failed:", detail);
        setError(detail.error ?? "Kunne ikke starte boken.");
        return;
      }

      const { book_id } = (await res.json()) as { book_id: string };
      router.push(`/book/${book_id}`);
    });
  }

  const canSubmit = Boolean(file && consent && !pending);

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-8">
      <FileUpload
        file={file}
        previewUrl={previewUrl}
        onChange={handleFileChange}
        disabled={pending}
      />

      <fieldset className="flex flex-col gap-3">
        <legend className="font-sans text-sm uppercase tracking-[0.16em] text-[color:var(--color-ink-soft)]">
          Stil
        </legend>
        <div className="grid gap-3 sm:grid-cols-3">
          {STYLES.map((opt) => (
            <label
              key={opt.id}
              className={`cursor-pointer rounded-2xl border p-4 text-left transition ${
                style === opt.id
                  ? "border-[color:var(--color-primary)] bg-white shadow-sm"
                  : "border-black/10 bg-white/60 hover:border-black/20"
              }`}
            >
              <input
                type="radio"
                name="style"
                value={opt.id}
                checked={style === opt.id}
                onChange={() => setStyle(opt.id)}
                className="sr-only"
                disabled={pending}
              />
              <span className="font-serif text-lg">{opt.label}</span>
              <span className="mt-1 block font-sans text-sm text-[color:var(--color-ink-soft)]">
                {opt.body}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <label className="flex flex-col gap-2">
        <span className="font-sans text-sm uppercase tracking-[0.16em] text-[color:var(--color-ink-soft)]">
          Tittel <span className="normal-case opacity-60">(valgfritt)</span>
        </span>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Eventyret om Lina"
          maxLength={80}
          disabled={pending}
          className="rounded-xl border border-black/10 bg-white/80 px-4 py-3 font-sans text-base outline-none focus:border-[color:var(--color-primary)] focus:ring-2 focus:ring-[color:var(--color-primary)]/30"
        />
      </label>

      <label className="flex items-start gap-3 rounded-2xl border border-black/10 bg-white/60 p-4">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          disabled={pending}
          className="mt-1 h-5 w-5 accent-[color:var(--color-primary)]"
        />
        <span className="font-sans text-sm text-[color:var(--color-ink-soft)]">
          Jeg har samtykke fra barnets foresatte til å bruke dette bildet.
          Bildet lagres privat, brukes kun for å lage denne boken, og slettes
          når kontoen slettes. Det brukes aldri til å trene noen modell.
        </span>
      </label>

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
        <div className="flex h-48 w-48 items-center justify-center rounded-xl bg-[color:var(--color-marigold)]/30 font-serif text-5xl text-[color:var(--color-ink-soft)]">
          +
        </div>
      )}
      <span className="font-sans text-sm text-[color:var(--color-ink-soft)]">
        {file ? file.name : "Trykk for å velge et bilde"}
      </span>
      <span className="font-sans text-xs text-[color:var(--color-ink-soft)]/70">
        JPG, PNG eller HEIC. Maks 8 MB.
      </span>
    </label>
  );
}
