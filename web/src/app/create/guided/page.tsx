import Link from "next/link";
import { GuidedWizard } from "./guided-wizard";

export default function CreateGuidedPage() {
  return (
    <main className="flex-1">
      <section className="mx-auto max-w-2xl px-6 pt-16 pb-6 text-center">
        <p className="font-sans text-sm uppercase tracking-[0.18em] text-[color:var(--color-ink-soft)]">
          Veiledet eventyr
        </p>
        <h1 className="mt-4 font-serif text-4xl leading-tight sm:text-5xl">
          Vi spør,{" "}
          <span className="italic text-[color:var(--color-primary)]">dere svarer</span>
        </h1>
        <p className="mt-4 font-sans text-base text-[color:var(--color-ink-soft)]">
          Fire enkle spørsmål — så vever vi resten.
        </p>
      </section>

      <section className="mx-auto max-w-2xl px-6 pb-20">
        <GuidedWizard />
      </section>

      <nav className="mx-auto max-w-2xl px-6 pb-16 text-center">
        <Link
          href="/create"
          className="font-sans text-sm text-[color:var(--color-ink-soft)] underline-offset-4 hover:underline"
        >
          ← Velg en annen inngang
        </Link>
      </nav>
    </main>
  );
}
