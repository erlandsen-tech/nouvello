import { NextResponse, type NextRequest } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { inngest } from "@/lib/inngest";

type CreateBookBody = {
  input_kind: "write" | "guided" | "photo" | "drawing";
  input_payload?: Record<string, unknown>;
  title?: string;
  language?: string;
  child_photo_url?: string;
  art_style?: string;
};

const VALID_INPUT_KINDS = new Set([
  "write",
  "guided",
  "photo",
  "drawing",
] as const);

const VALID_TARGET_MINUTES = new Set([2, 5, 10]);
const MIN_WRITE_CHARS = 80;
const MAX_WRITE_CHARS = 4000;

function validatePayload(body: CreateBookBody): string | null {
  const payload = body.input_payload ?? {};

  if (
    payload.target_minutes !== undefined &&
    !VALID_TARGET_MINUTES.has(payload.target_minutes as number)
  ) {
    return "invalid_target_minutes";
  }

  if (body.input_kind === "write") {
    const text = typeof payload.text === "string" ? payload.text.trim() : "";
    if (text.length < MIN_WRITE_CHARS) return "text_too_short";
    if (text.length > MAX_WRITE_CHARS) return "text_too_long";
  }

  if (body.input_kind === "photo" && !body.child_photo_url) {
    return "missing_child_photo_url";
  }

  return null;
}

export async function POST(request: NextRequest) {
  const supabase = await createSupabaseServerClient();
  const { data: claimsData } = await supabase.auth.getClaims();
  if (!claimsData) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }
  const userId = claimsData.claims.sub;

  let body: CreateBookBody;
  try {
    body = (await request.json()) as CreateBookBody;
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  if (!VALID_INPUT_KINDS.has(body.input_kind)) {
    return NextResponse.json(
      { error: "invalid_input_kind" },
      { status: 400 },
    );
  }

  const validation = validatePayload(body);
  if (validation) {
    return NextResponse.json(
      { error: validation },
      { status: 400 },
    );
  }

  const { data: book, error: insertError } = await supabase
    .from("books")
    .insert({
      user_id: userId,
      input_kind: body.input_kind,
      input_payload: body.input_payload ?? {},
      title: body.title?.trim() || "Uten tittel",
      language: body.language ?? "nb-NO",
      child_photo_url: body.child_photo_url ?? null,
      art_style: body.art_style ?? null,
      status: "queued",
    })
    .select("id")
    .single();

  if (insertError || !book) {
    console.error("[api/books] insert failed:", insertError);
    return NextResponse.json(
      { error: "insert_failed", detail: insertError?.message },
      { status: 500 },
    );
  }

  try {
    await inngest.send({
      name: "book.generate",
      data: { book_id: book.id },
    });
  } catch (err) {
    console.error("[api/books] inngest.send failed:", err);
    // Roll back the book row so we don't leave it stuck in 'queued' forever.
    await supabase.from("books").delete().eq("id", book.id);
    return NextResponse.json(
      { error: "enqueue_failed" },
      { status: 502 },
    );
  }

  return NextResponse.json({ book_id: book.id }, { status: 201 });
}
