"use client";

import { useActionState } from "react";
import { sendMagicLink, type LoginState } from "./actions";

const INITIAL: LoginState = { status: "idle" };

export function LoginForm({ next }: { next: string }) {
  const [state, action, pending] = useActionState(sendMagicLink, INITIAL);

  if (state.status === "sent") {
    return (
      <div className="rounded-2xl border border-black/10 bg-white/60 p-6 text-center">
        <p className="font-serif text-2xl">Sjekk e-posten din</p>
        <p className="mt-3 font-sans text-base text-[color:var(--color-ink-soft)]">
          Vi sendte en magisk lenke til{" "}
          <span className="text-[color:var(--color-ink)]">{state.message}</span>.
          Trykk på den for å logge inn.
        </p>
      </div>
    );
  }

  return (
    <form action={action} className="flex flex-col gap-3">
      <input type="hidden" name="next" value={next} />
      <label className="font-sans text-sm text-[color:var(--color-ink-soft)]">
        E-post
        <input
          type="email"
          name="email"
          required
          autoComplete="email"
          placeholder="navn@eksempel.no"
          className="mt-1 w-full rounded-xl border border-black/10 bg-white/80 px-4 py-3 font-sans text-base outline-none focus:border-[color:var(--color-primary)] focus:ring-2 focus:ring-[color:var(--color-primary)]/30"
        />
      </label>

      {state.status === "error" && state.message ? (
        <p className="font-sans text-sm text-red-700">{state.message}</p>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        className="mt-2 inline-flex items-center justify-center rounded-full bg-[color:var(--color-primary)] px-6 py-3 font-sans text-base font-medium text-[color:var(--color-primary-ink)] shadow-sm transition hover:brightness-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-primary)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--color-surface)] disabled:opacity-60"
      >
        {pending ? "Sender …" : "Send magisk lenke"}
      </button>

      <p className="mt-1 text-center font-sans text-xs text-[color:var(--color-ink-soft)]">
        Vi sender en engangs-lenke. Ingen passord å huske på.
      </p>
    </form>
  );
}
