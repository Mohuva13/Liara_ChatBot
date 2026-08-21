import { describe, expect, it } from "vitest";

import { mapBackendStream } from "./backend-stream";

const encoder = new TextEncoder();
const decoder = new TextDecoder();

function backendEvent(event: Record<string, unknown>) {
  return `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
}

function sourceFromPieces(pieces: string[]) {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const piece of pieces) {
        controller.enqueue(encoder.encode(piece));
      }
      controller.close();
    },
  });
}

async function readUIChunks(stream: ReadableStream<Uint8Array>) {
  const text = decoder.decode(await new Response(stream).arrayBuffer());
  return text
    .split("\n\n")
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => block.replace(/^data: /, ""))
    .map((data) => (data === "[DONE]" ? data : JSON.parse(data)));
}

describe("backend SSE to AI SDK UI stream", () => {
  it("maps split text, canonical sources, metadata, and finish", async () => {
    const payload = [
      backendEvent({ type: "message_start", response_id: "response-1" }),
      backendEvent({ type: "text_delta", text: "پاسخ " }),
      backendEvent({ type: "text_delta", text: "مستند" }),
      backendEvent({
        type: "sources",
        sources: [
          {
            id: "source-1",
            title: "عنوان سند",
            url: "https://docs.liara.ir/example/",
            section: "بخش",
            snippet: "گزیده",
            source_commit: "commit",
          },
        ],
      }),
      backendEvent({ type: "message_end", finish_reason: "stop" }),
    ].join("");
    const middle = Math.floor(payload.length / 2);

    const chunks = await readUIChunks(
      mapBackendStream(
        sourceFromPieces([payload.slice(0, middle), payload.slice(middle)]),
      ),
    );

    expect(chunks).toContainEqual({ type: "start", messageId: "response-1" });
    expect(chunks).toContainEqual({
      type: "text-delta",
      id: "text-response-1",
      delta: "پاسخ ",
    });
    expect(chunks).toContainEqual({
      type: "source-url",
      sourceId: "source-1",
      url: "https://docs.liara.ir/example/",
      title: "عنوان سند",
    });
    expect(chunks).toContainEqual({
      type: "finish",
      finishReason: "stop",
    });
    expect(chunks.at(-1)).toBe("[DONE]");
  });

  it("maps support into a typed persistent data part", async () => {
    const payload = [
      backendEvent({ type: "message_start", response_id: "response-2" }),
      backendEvent({
        type: "support",
        reason_code: "insufficient_evidence",
        ticket_url: "https://console.liara.ir/tickets/create",
        summary: "خلاصه",
        text: "پاسخ مطمئن پیدا نشد.",
      }),
      backendEvent({ type: "message_end", finish_reason: "policy" }),
    ].join("");

    const chunks = await readUIChunks(
      mapBackendStream(sourceFromPieces([payload])),
    );

    expect(chunks).toContainEqual({
      type: "data-support",
      data: {
        reasonCode: "insufficient_evidence",
        ticketUrl: "https://console.liara.ir/tickets/create",
        summary: "خلاصه",
        text: "پاسخ مطمئن پیدا نشد.",
      },
    });
  });

  it("preserves the safe backend error message", async () => {
    const payload = [
      backendEvent({ type: "message_start", response_id: "response-3" }),
      backendEvent({
        type: "error",
        code: "provider_timeout",
        message: "سرویس تولید پاسخ موقتاً در دسترس نیست.",
        retryable: true,
      }),
    ].join("");

    const chunks = await readUIChunks(
      mapBackendStream(sourceFromPieces([payload])),
    );

    expect(chunks).toContainEqual({
      type: "error",
      errorText: "سرویس تولید پاسخ موقتاً در دسترس نیست.",
    });
  });
});
