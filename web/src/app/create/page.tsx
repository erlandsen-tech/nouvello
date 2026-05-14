import Link from "next/link";

type Mode = {
  href: string;
  eyebrow: string;
  title: string;
  body: string;
  accent: string;
};

const MODES: Mode[] = [
  {
    href: "/create/photo",
    eyebrow: "Bilde av barnet",
    title: "Barnet er helten",
    body: "Last opp et portrett. Vi tegner barnet inn i historien — gjenkjennelig på hver side.",
    accent: "var(--color-marigold)",
  },
  {
    href: "/create/drawing",
    eyebrow: "Bilde av en tegning",
    title: "Få tegningen til å leve",
    body: "Ta bilde av en tegning hjemmefra. Vi gjør den om til en figur i et eventyr.",
    accent: "var(--color-sky)",
  },
  {
    href: "/create/guided",
    eyebrow: "Veiledet eventyr",
    title: "Lag det sammen, steg for steg",
    body: "Vi spør om helten, stedet og oppdraget. Dere bestemmer, vi vever.",
    accent: "var(--color-sage)",
  },
  {
    href: "/create/write",
    eyebrow: "Skriv selv",
    title: "Egen historie",
    body: "Har dere allerede en idé eller en tekst? Lim den inn — vi illustrerer.",
    accent: "var(--color-primary)",
  },
];

export default function CreatePage() {
  return (
    <main className="flex-1">
      <section className="mx-auto max-w-3xl px-6 pt-20 pb-10 text-center">
        <p className="font-sans text-sm uppercase tracking-[0.18em] text-[color:var(--color-ink-soft)]">
          Steg 1 av 3
        </p>
        <h1 className="mt-6 font-serif text-4xl leading-[1.1] sm:text-5xl">
          Hvordan vil dere{" "}
          <span className="italic text-[color:var(--color-primary)]">begynne</span>
          ?
        </h1>
        <p className="mt-5 font-sans text-lg text-[color:var(--color-ink-soft)]">
          Velg en inngang. Dere kan alltid bytte underveis.
        </p>
      </section>

      <section className="mx-auto grid max-w-5xl gap-5 px-6 pb-20 sm:grid-cols-2">
        {MODES.map((mode) => (
          <ModeCard key={mode.href} mode={mode} />
        ))}
      </section>

      <nav className="mx-auto max-w-5xl px-6 pb-16 text-center">
        <Link
          href="/"
          className="font-sans text-sm text-[color:var(--color-ink-soft)] underline-offset-4 hover:underline"
        >
          ← Tilbake
        </Link>
      </nav>
    </main>
  );
}

function ModeCard({ mode }: { mode: Mode }) {
  return (
    <Link
      href={mode.href}
      className="group relative flex flex-col gap-4 rounded-2xl border border-black/10 bg-white/60 p-7 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-black/20 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-primary)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--color-surface)]"
    >
      <span
        aria-hidden="true"
        className="absolute left-7 top-7 h-2 w-12 rounded-full"
        style={{ background: mode.accent }}
      />
      <div className="pt-6">
        <p className="font-sans text-xs uppercase tracking-[0.16em] text-[color:var(--color-ink-soft)]">
          {mode.eyebrow}
        </p>
        <h2 className="mt-2 font-serif text-2xl leading-tight">{mode.title}</h2>
        <p className="mt-3 font-sans text-base text-[color:var(--color-ink-soft)]">
          {mode.body}
        </p>
      </div>
      <span className="mt-auto inline-flex items-center font-sans text-sm font-medium text-[color:var(--color-primary)]">
        Velg denne
        <span
          aria-hidden="true"
          className="ml-1 transition group-hover:translate-x-0.5"
        >
          →
        </span>
      </span>
    </Link>
  );
}
