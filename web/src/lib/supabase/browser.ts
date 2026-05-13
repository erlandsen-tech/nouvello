"use client";

import { createBrowserClient } from "@supabase/ssr";

/** Singleton browser client, safe to import from Client Components. */
export function createSupabaseBrowserClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
