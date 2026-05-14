import Link from "next/link";
import { PhotoForm } from "./photo-form";

export default function CreatePhotoPage() {
  return (
    <main className="flex-1">
      <section className="mx-auto max-w-2xl px-6 pt-16 pb-8 text-center">
        <p className="font-sans text-sm uppercase tracking-[0.18em] text-[color:var(--color-ink-soft)]">
          Bilde av barnet
        </p>
        <h1 className="mt-4 font-serif text-4xl leading-tight sm:text-5xl">
          Barnet er{" "}
          <span className="italic text-[color:var(--color-primary)]">helten</span>
        </h1>
        <p className="mt-4 font-sans text-base text-[color:var(--color-ink-soft)]">
          Last opp et tydelig portrett. Vi tegner barnet inn i hver scene —
          gjenkjennelig fra side til side.
        </p>
      </section>

      <section className="mx-auto max-w-2xl px-6 pb-20">
        <PhotoForm />
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
