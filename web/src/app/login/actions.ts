"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export type LoginState = {
  status: "idle" | "sent" | "error";
  message?: string;
};

export async function sendMagicLink(
  _prev: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const email = String(formData.get("email") ?? "")
    .trim()
    .toLowerCase();
  const next = String(formData.get("next") ?? "/library");

  if (!email || !email.includes("@")) {
    return { status: "error", message: "Skriv inn en gyldig e-postadresse." };
  }

  const supabase = await createSupabaseServerClient();
  const headerList = await headers();
  const origin =
    headerList.get("origin") ??
    (headerList.get("host")
      ? `${headerList.get("x-forwarded-proto") ?? "https"}://${headerList.get(
          "host",
        )}`
      : "");

  const callbackUrl = new URL("/auth/callback", origin || "http://localhost:3000");
  callbackUrl.searchParams.set("next", next);

  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: { emailRedirectTo: callbackUrl.toString() },
  });

  if (error) {
    return { status: "error", message: error.message };
  }

  return { status: "sent", message: email };
}

export async function signOut() {
  const supabase = await createSupabaseServerClient();
  await supabase.auth.signOut();
  redirect("/");
}
