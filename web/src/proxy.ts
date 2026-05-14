import { NextResponse, type NextRequest } from "next/server";
import { createSupabaseProxyClient } from "@/lib/supabase/proxy";

const PROTECTED_PREFIXES = ["/create", "/library", "/account", "/book"];

export async function proxy(request: NextRequest) {
  const { supabase, response } = createSupabaseProxyClient(request);

  // Trigger token refresh + verify the JWT.
  const { data } = await supabase.auth.getClaims();

  const path = request.nextUrl.pathname;
  const needsAuth = PROTECTED_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`),
  );

  if (needsAuth && !data) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", path + request.nextUrl.search);
    return NextResponse.redirect(loginUrl);
  }

  return response();
}

export const config = {
  // Skip Next.js internals + static files. Auth refresh still runs on
  // every page request, which is what @supabase/ssr expects.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|avif)$).*)"],
};
