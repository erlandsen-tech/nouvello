import Link from "next/link";
import { WriteForm } from "./write-form";

export default function CreateWritePage() {
  return (
    <main className="flex-1">
      <section className="mx-auto max-w-2xl px-6 pt-16 pb-8 text-center">
        <p className="font-sans text-sm uppercase tracking-[0.18em] text-[color:var(--color-ink-soft)]">
          Skriv selv
        </p>
        <h1 className="mt-4 font-serif text-4xl leading-tight sm:text-5xl">
          Egen{" "}
          <span className="italic text-[color:var(--color-primary)]">historie</span>
        </h1>
        <p className="mt-4 font-sans text-base text-[color:var(--color-ink-soft)]">
          Lim inn eller skriv en historie. Vi tar oss av illustrasjonene.
        </p>
      </section>

      <section className="mx-auto max-w-2xl px-6 pb-20">
        <WriteForm />
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
