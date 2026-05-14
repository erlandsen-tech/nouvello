import Link from "next/link";
import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { LoginForm } from "./login-form";

type SearchParams = Promise<{ next?: string; error?: string }>;

const ERROR_MESSAGES: Record<string, string> = {
  missing_code:
    "Lenken manglet en kode. Sannsynligvis er e-postmalen i Supabase satt opp for en eldre flyt — sjekk at den bruker token_hash-mønsteret.",
  exchange_failed:
    "Kunne ikke veksle inn lenken. Den kan være utgått eller allerede brukt — be om en ny.",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { next, error } = await searchParams;
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getClaims();

  if (data) {
    redirect(next || "/library");
  }

  const errorMessage = error
    ? ERROR_MESSAGES[error] ?? `Auth-feil: ${error}`
    : null;

  return (
    <main className="flex-1">
      <section className="mx-auto flex max-w-md flex-col gap-8 px-6 pt-24 pb-16">
        <div className="text-center">
          <p className="font-sans text-sm uppercase tracking-[0.18em] text-[color:var(--color-ink-soft)]">
            Drømmevev
          </p>
          <h1 className="mt-4 font-serif text-4xl leading-tight">
            Logg inn
          </h1>
          <p className="mt-3 font-sans text-base text-[color:var(--color-ink-soft)]">
            Vi sender en lenke til e-posten din.
          </p>
        </div>

        {errorMessage ? (
          <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 font-sans text-sm text-red-800">
            {errorMessage}
          </div>
        ) : null}

        <LoginForm next={next || "/library"} />

        <p className="text-center font-sans text-xs text-[color:var(--color-ink-soft)]">
          <Link href="/" className="underline-offset-2 hover:underline">
            ← Tilbake til forsiden
          </Link>
        </p>
      </section>
    </main>
  );
}
