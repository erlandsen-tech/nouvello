import { NextResponse, type NextRequest } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/server";

/**
 * Magic-link callback. Supabase redirects here with `?code=...` (PKCE flow).
 * We exchange the code for a session, which sets auth cookies, then send
 * the user on to wherever they were trying to go.
 */
export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const tokenHash = url.searchParams.get("token_hash");
  const type = url.searchParams.get("type");
  const next = url.searchParams.get("next") || "/library";

  console.log("[auth/callback]", {
    hasCode: Boolean(code),
    hasTokenHash: Boolean(tokenHash),
    type,
    allParams: Object.fromEntries(url.searchParams),
  });

  const supabase = await createSupabaseServerClient();

  // PKCE flow (default for `signInWithOtp` via @supabase/ssr).
  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) {
      console.error("[auth/callback] exchangeCodeForSession failed:", error);
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("error", "exchange_failed");
      return NextResponse.redirect(loginUrl);
    }
    return NextResponse.redirect(new URL(next, request.url));
  }

  // token_hash flow (used by older default email templates).
  if (tokenHash && type) {
    const { error } = await supabase.auth.verifyOtp({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      type: type as any,
      token_hash: tokenHash,
    });
    if (error) {
      console.error("[auth/callback] verifyOtp failed:", error);
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("error", "exchange_failed");
      return NextResponse.redirect(loginUrl);
    }
    return NextResponse.redirect(new URL(next, request.url));
  }

  return NextResponse.redirect(
    new URL("/login?error=missing_code", request.url),
  );
}
