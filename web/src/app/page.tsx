import Image from "next/image";
import Link from "next/link";

const SAMPLES = [
  { src: "/illustrations/bedroom-to-forest.png", alt: "Et soverom som blir til en skog" },
  { src: "/illustrations/spread-yeti.png", alt: "Et barn møter en snill fabelfigur" },
  { src: "/illustrations/spread-paper-airplane.png", alt: "Et barn flyr på et papirfly" },
  { src: "/illustrations/mirror-magic.png", alt: "Et barn foran et magisk speil" },
];

export default function HomePage() {
  return (
    <main className="flex-1">
      <section className="mx-auto grid max-w-5xl items-center gap-12 px-6 pt-16 pb-12 sm:grid-cols-[1.1fr_1fr] sm:pt-24">
        <div className="text-center sm:text-left">
          <p className="font-sans text-sm uppercase tracking-[0.18em] text-[color:var(--color-ink-soft)]">
            Drømmevev fra aiakaki
          </p>
          <h1 className="mt-6 font-serif text-5xl leading-[1.05] sm:text-6xl">
            Lag leggetidshistorier{" "}
            <span className="italic text-[color:var(--color-primary)]">sammen</span>
            .
          </h1>
          <p className="mt-6 font-sans text-lg text-[color:var(--color-ink-soft)] sm:text-xl">
            Personlige bildebøker med barnet i hovedrollen — drømt frem i kveld,
            ferdig før godnatt-koset.
          </p>

          <Link
            href="/create"
            className="mt-10 inline-flex items-center justify-center rounded-full bg-[color:var(--color-primary)] px-8 py-4 font-sans text-base font-medium text-[color:var(--color-primary-ink)] shadow-sm transition hover:brightness-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-primary)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--color-surface)]"
          >
            Lag en bok sammen
          </Link>

          <p className="mt-4 font-sans text-sm text-[color:var(--color-ink-soft)]">
            Første bok er gratis å prøve.
          </p>
        </div>

        <div className="relative aspect-[4/3] overflow-hidden rounded-3xl shadow-lg">
          <Image
            src="/illustrations/hero-photo.png"
            alt="En far og et barn leser sammen"
            fill
            sizes="(min-width: 640px) 50vw, 100vw"
            priority
            className="object-cover"
          />
        </div>
      </section>

      <section className="mx-auto grid max-w-4xl gap-8 px-6 py-16 sm:grid-cols-3">
        <Step
          number="1"
          title="Velg en helt"
          body="Et bilde av barnet, en tegning, eller bare en idé. Vi tar det derfra."
        />
        <Step
          number="2"
          title="Tegn en verden"
          body="Skog, romstasjon, undervannsby — dere bestemmer hvor eventyret skjer."
        />
        <Step
          number="3"
          title="Vev en historie"
          body="Drømmevev fletter bilder og ord til en bok på under et minutt."
        />
      </section>

      <section className="mx-auto max-w-5xl px-6 pb-20">
        <p className="text-center font-sans text-sm uppercase tracking-[0.18em] text-[color:var(--color-ink-soft)]">
          Smakebiter
        </p>
        <h2 className="mt-3 text-center font-serif text-3xl">
          Slik kan boken se ut
        </h2>
        <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {SAMPLES.map((sample) => (
            <div
              key={sample.src}
              className="relative aspect-square overflow-hidden rounded-2xl bg-white shadow-sm"
            >
              <Image
                src={sample.src}
                alt={sample.alt}
                fill
                sizes="(min-width: 640px) 25vw, 50vw"
                className="object-cover"
              />
            </div>
          ))}
        </div>
      </section>

      <footer className="mt-auto border-t border-black/5 py-6">
        <p className="text-center font-sans text-xs text-[color:var(--color-ink-soft)]">
          Drømmevev fra aiakaki · © 2026 ·{" "}
          <Link href="/privacy" className="underline-offset-2 hover:underline">
            Personvern
          </Link>{" "}
          ·{" "}
          <Link href="/terms" className="underline-offset-2 hover:underline">
            Vilkår
          </Link>
        </p>
      </footer>
    </main>
  );
}

function Step({
  number,
  title,
  body,
}: {
  number: string;
  title: string;
  body: string;
}) {
  return (
    <div>
      <span className="font-serif text-3xl text-[color:var(--color-primary)]">
        {number}
      </span>
      <h3 className="mt-2 font-serif text-2xl">{title}</h3>
      <p className="mt-2 font-sans text-base text-[color:var(--color-ink-soft)]">
        {body}
      </p>
    </div>
  );
}
