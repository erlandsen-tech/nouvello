"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

const LENGTHS = [
  { minutes: 2, label: "Kort", body: "~5 sider" },
  { minutes: 5, label: "Mellomlang", body: "~10 sider" },
  { minutes: 10, label: "Lang", body: "~15 sider" },
] as const;

type Minutes = (typeof LENGTHS)[number]["minutes"];

export function GuidedWizard() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  const [heroName, setHeroName] = useState("");
  const [heroAge, setHeroAge] = useState("");
  const [heroTraits, setHeroTraits] = useState("");
  const [setting, setSetting] = useState("");
  const [adventure, setAdventure] = useState("");
  const [lessonEnabled, setLessonEnabled] = useState(false);
  const [lesson, setLesson] = useState("");
  const [minutes, setMinutes] = useState<Minutes>(5);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const canAdvance = (() => {
    if (pending) return false;
    if (step === 1) return heroName.trim().length >= 2;
    if (step === 2) return setting.trim().length >= 4;
    if (step === 3) return adventure.trim().length >= 6;
    if (step === 4) return !lessonEnabled || lesson.trim().length >= 4;
    return false;
  })();

  // Step 4 only matters if lesson is on; otherwise step 3 finishes.
  const isFinalStep = step === 4 || (step === 3 && !lessonEnabled);
  const totalSteps = lessonEnabled ? 4 : 3;
  const visibleStep = step;

  function next() {
    if (!canAdvance) return;
    if (isFinalStep) {
      submit();
      return;
    }
    setStep((s) => (s < 4 ? ((s + 1) as 2 | 3 | 4) : 4));
  }

  function back() {
    setError(null);
    setStep((s) => (s > 1 ? ((s - 1) as 1 | 2 | 3) : 1));
  }

  function submit() {
    setError(null);
    startTransition(async () => {
      const res = await fetch("/api/books", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input_kind: "guided",
          title: `${heroName.trim()} og ${adventure.trim().slice(0, 40)}`,
          input_payload: {
            hero: {
              name: heroName.trim(),
              age: heroAge.trim() || null,
              traits: heroTraits.trim() || null,
            },
            setting: setting.trim(),
            adventure: adventure.trim(),
            lesson: lessonEnabled ? lesson.trim() : null,
            target_minutes: minutes,
          },
        }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        console.error("[guided] /api/books failed:", detail);
        setError(detail.error ?? "Kunne ikke starte boken.");
        return;
      }

      const { book_id } = (await res.json()) as { book_id: string };
      router.push(`/book/${book_id}`);
    });
  }

  return (
    <div className="flex flex-col gap-8">
      <Progress current={visibleStep} total={totalSteps} />

      {step === 1 ? (
        <HeroStep
          name={heroName}
          age={heroAge}
          traits={heroTraits}
          onName={setHeroName}
          onAge={setHeroAge}
          onTraits={setHeroTraits}
          disabled={pending}
        />
      ) : null}

      {step === 2 ? (
        <SettingStep value={setting} onChange={setSetting} disabled={pending} />
      ) : null}

      {step === 3 ? (
        <AdventureStep
          adventure={adventure}
          onAdventure={setAdventure}
          lessonEnabled={lessonEnabled}
          onLessonEnabled={setLessonEnabled}
          minutes={minutes}
          onMinutes={setMinutes}
          disabled={pending}
        />
      ) : null}

      {step === 4 ? (
        <LessonStep value={lesson} onChange={setLesson} disabled={pending} />
      ) : null}

      {error ? (
        <p className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 font-sans text-sm text-red-800">
          {error}
        </p>
      ) : null}

      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={back}
          disabled={step === 1 || pending}
          className="font-sans text-sm text-[color:var(--color-ink-soft)] underline-offset-4 hover:underline disabled:invisible"
        >
          ← Forrige
        </button>
        <button
          type="button"
          onClick={next}
          disabled={!canAdvance}
          className="inline-flex items-center justify-center rounded-full bg-[color:var(--color-primary)] px-6 py-3 font-sans text-base font-medium text-[color:var(--color-primary-ink)] shadow-sm transition hover:brightness-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-primary)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--color-surface)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {pending
            ? "Veving …"
            : isFinalStep
              ? "Lag boken"
              : "Neste →"}
        </button>
      </div>
    </div>
  );
}

function Progress({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center justify-center gap-2">
      {Array.from({ length: total }).map((_, i) => {
        const idx = i + 1;
        const active = idx === current;
        const done = idx < current;
        return (
          <span
            key={idx}
            className={`h-1.5 w-12 rounded-full transition-colors ${
              done
                ? "bg-[color:var(--color-primary)]"
                : active
                  ? "bg-[color:var(--color-primary)]/60"
                  : "bg-black/10"
            }`}
          />
        );
      })}
    </div>
  );
}

function HeroStep(props: {
  name: string;
  age: string;
  traits: string;
  onName: (v: string) => void;
  onAge: (v: string) => void;
  onTraits: (v: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex flex-col gap-5">
      <header>
        <h2 className="font-serif text-3xl leading-tight">Hvem er helten?</h2>
        <p className="mt-1 font-sans text-base text-[color:var(--color-ink-soft)]">
          Bare navnet er nok. Resten gjør historien morsommere.
        </p>
      </header>

      <Field label="Navn">
        <input
          type="text"
          value={props.name}
          onChange={(e) => props.onName(e.target.value)}
          placeholder="Lina"
          maxLength={40}
          disabled={props.disabled}
          className={inputClass}
        />
      </Field>

      <Field label="Alder (valgfritt)">
        <input
          type="text"
          value={props.age}
          onChange={(e) => props.onAge(e.target.value)}
          placeholder="4 år"
          maxLength={20}
          disabled={props.disabled}
          className={inputClass}
        />
      </Field>

      <Field label="Tre ord som beskriver helten (valgfritt)">
        <input
          type="text"
          value={props.traits}
          onChange={(e) => props.onTraits(e.target.value)}
          placeholder="modig, nysgjerrig, tøysete"
          maxLength={120}
          disabled={props.disabled}
          className={inputClass}
        />
      </Field>
    </div>
  );
}

function SettingStep(props: {
  value: string;
  onChange: (v: string) => void;
  disabled: boolean;
}) {
  const presets = ["en mørk skog", "en undervannsby", "en romstasjon", "et lite kjøkken om natten"];
  return (
    <div className="flex flex-col gap-5">
      <header>
        <h2 className="font-serif text-3xl leading-tight">Hvor skjer det?</h2>
        <p className="mt-1 font-sans text-base text-[color:var(--color-ink-soft)]">
          Et sted, en stemning — vi vet hva vi skal med det.
        </p>
      </header>

      <Field label="Stedet">
        <input
          type="text"
          value={props.value}
          onChange={(e) => props.onChange(e.target.value)}
          placeholder="en hage som blir levende om natten"
          maxLength={140}
          disabled={props.disabled}
          className={inputClass}
        />
      </Field>

      <div className="flex flex-wrap gap-2">
        {presets.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => props.onChange(p)}
            disabled={props.disabled}
            className="rounded-full border border-black/10 bg-white/60 px-3 py-1.5 font-sans text-sm text-[color:var(--color-ink-soft)] transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-ink)]"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

function AdventureStep(props: {
  adventure: string;
  onAdventure: (v: string) => void;
  lessonEnabled: boolean;
  onLessonEnabled: (v: boolean) => void;
  minutes: Minutes;
  onMinutes: (v: Minutes) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h2 className="font-serif text-3xl leading-tight">Hva skal skje?</h2>
        <p className="mt-1 font-sans text-base text-[color:var(--color-ink-soft)]">
          Et oppdrag, et problem, en ting som må reddes.
        </p>
      </header>

      <Field label="Eventyret">
        <textarea
          value={props.adventure}
          onChange={(e) => props.onAdventure(e.target.value.slice(0, 280))}
          placeholder="Helten må finne den siste stjernen før morgenen kommer."
          rows={3}
          disabled={props.disabled}
          className={textareaClass}
        />
      </Field>

      <fieldset className="flex flex-col gap-3">
        <legend className="font-sans text-sm uppercase tracking-[0.16em] text-[color:var(--color-ink-soft)]">
          Lesetid
        </legend>
        <div className="grid gap-3 sm:grid-cols-3">
          {LENGTHS.map((opt) => (
            <label
              key={opt.minutes}
              className={`cursor-pointer rounded-2xl border p-4 text-left transition ${
                props.minutes === opt.minutes
                  ? "border-[color:var(--color-primary)] bg-white shadow-sm"
                  : "border-black/10 bg-white/60 hover:border-black/20"
              }`}
            >
              <input
                type="radio"
                name="minutes"
                value={opt.minutes}
                checked={props.minutes === opt.minutes}
                onChange={() => props.onMinutes(opt.minutes)}
                className="sr-only"
                disabled={props.disabled}
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

      <label className="flex items-center gap-3 rounded-2xl border border-black/10 bg-white/60 p-4">
        <input
          type="checkbox"
          checked={props.lessonEnabled}
          onChange={(e) => props.onLessonEnabled(e.target.checked)}
          disabled={props.disabled}
          className="h-5 w-5 accent-[color:var(--color-primary)]"
        />
        <span className="font-sans text-sm text-[color:var(--color-ink-soft)]">
          Skal historien ha en lærdom?{" "}
          <span className="opacity-70">(valgfritt)</span>
        </span>
      </label>
    </div>
  );
}

function LessonStep(props: {
  value: string;
  onChange: (v: string) => void;
  disabled: boolean;
}) {
  const presets = ["om mot", "om vennskap", "om å dele", "om å være tålmodig"];
  return (
    <div className="flex flex-col gap-5">
      <header>
        <h2 className="font-serif text-3xl leading-tight">Hva skal vi lære?</h2>
        <p className="mt-1 font-sans text-base text-[color:var(--color-ink-soft)]">
          Noen få ord — vi vever det inn så det ikke blir pekefinger.
        </p>
      </header>

      <Field label="Lærdommen">
        <input
          type="text"
          value={props.value}
          onChange={(e) => props.onChange(e.target.value)}
          placeholder="om å tørre å spørre om hjelp"
          maxLength={140}
          disabled={props.disabled}
          className={inputClass}
        />
      </Field>

      <div className="flex flex-wrap gap-2">
        {presets.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => props.onChange(p)}
            disabled={props.disabled}
            className="rounded-full border border-black/10 bg-white/60 px-3 py-1.5 font-sans text-sm text-[color:var(--color-ink-soft)] transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-ink)]"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="font-sans text-sm uppercase tracking-[0.16em] text-[color:var(--color-ink-soft)]">
        {label}
      </span>
      {children}
    </label>
  );
}

const inputClass =
  "rounded-xl border border-black/10 bg-white/80 px-4 py-3 font-sans text-base outline-none focus:border-[color:var(--color-primary)] focus:ring-2 focus:ring-[color:var(--color-primary)]/30";

const textareaClass =
  "rounded-xl border border-black/10 bg-white/80 px-4 py-4 font-serif text-base leading-relaxed outline-none focus:border-[color:var(--color-primary)] focus:ring-2 focus:ring-[color:var(--color-primary)]/30";
