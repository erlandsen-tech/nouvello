import Link from "next/link";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function SiteHeader() {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getClaims();
  const signedIn = Boolean(data);

  return (
    <header className="w-full border-b border-black/5 bg-[color:var(--color-surface)]/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link
          href="/"
          className="font-serif text-xl tracking-tight text-[color:var(--color-ink)]"
        >
          Drømmevev
        </Link>

        <nav className="flex items-center gap-5 font-sans text-sm">
          {signedIn ? (
            <>
              <Link
                href="/library"
                className="text-[color:var(--color-ink-soft)] hover:text-[color:var(--color-ink)]"
              >
                Mitt bibliotek
              </Link>
              <form action="/auth/signout" method="post">
                <button
                  type="submit"
                  className="text-[color:var(--color-ink-soft)] hover:text-[color:var(--color-ink)]"
                >
                  Logg ut
                </button>
              </form>
            </>
          ) : (
            <Link
              href="/login"
              className="text-[color:var(--color-ink-soft)] hover:text-[color:var(--color-ink)]"
            >
              Logg inn
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
