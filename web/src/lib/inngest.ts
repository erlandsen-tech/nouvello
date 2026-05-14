import "server-only";
import { Inngest } from "inngest";

/**
 * Inngest client for sending events from Next.js into the worker.
 *
 * In dev, the SDK auto-discovers `http://localhost:8288` (the inngest-cli dev
 * server). In production, set `INNGEST_EVENT_KEY` so events flow through
 * Inngest Cloud to the Fly.io worker.
 *
 * Functions themselves are defined in `worker/jobs.py`; Next.js never
 * registers — it only sends.
 */
export const inngest = new Inngest({
  id: "drommevev-web",
  eventKey: process.env.INNGEST_EVENT_KEY,
});

export type BookGenerateEvent = {
  name: "book.generate";
  data: { book_id: string };
};
