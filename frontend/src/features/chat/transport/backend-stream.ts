type BackendSource = {
  id: string;
  title: string;
  url: string;
  section?: string;
  snippet?: string;
  source_commit?: string;
};

type BackendEvent = {
  type: string;
  response_id?: string;
  text?: string;
  sources?: BackendSource[];
  suggestions?: string[];
  reason_code?: string;
  ticket_url?: string;
  summary?: string;
  usage?: {
    model_tier: "small" | "large" | "none";
    input_tokens?: number;
    output_tokens?: number;
    cached_tokens?: number;
    cache_hit?: boolean;
  };
  finish_reason?: string;
  code?: string;
  message?: string;
};

type UIChunk = Record<string, unknown>;

const encoder = new TextEncoder();

function encodeChunk(chunk: UIChunk | "[DONE]"): Uint8Array {
  return encoder.encode(
    chunk === "[DONE]"
      ? "data: [DONE]\n\n"
      : `data: ${JSON.stringify(chunk)}\n\n`,
  );
}

function finishReason(value: string | undefined) {
  return value === "stop" || value === "length" ? value : "other";
}

export function mapBackendStream(
  source: ReadableStream<Uint8Array>,
): ReadableStream<Uint8Array> {
  const reader = source.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let responseId = crypto.randomUUID();
  let textId = `text-${responseId}`;
  let textStarted = false;
  let finished = false;

  const closeText = (controller: ReadableStreamDefaultController<Uint8Array>) => {
    if (textStarted) {
      controller.enqueue(encodeChunk({ type: "text-end", id: textId }));
      textStarted = false;
    }
  };

  const emit = (
    event: BackendEvent,
    controller: ReadableStreamDefaultController<Uint8Array>,
  ) => {
    switch (event.type) {
      case "message_start":
        responseId = event.response_id ?? responseId;
        textId = `text-${responseId}`;
        controller.enqueue(
          encodeChunk({ type: "start", messageId: responseId }),
        );
        break;
      case "status":
        if (event.text) {
          controller.enqueue(
            encodeChunk({
              type: "data-status",
              data: { text: event.text },
              transient: true,
            }),
          );
        }
        break;
      case "text_delta":
        if (!textStarted) {
          controller.enqueue(encodeChunk({ type: "text-start", id: textId }));
          textStarted = true;
        }
        if (event.text) {
          controller.enqueue(
            encodeChunk({ type: "text-delta", id: textId, delta: event.text }),
          );
        }
        break;
      case "sources":
        closeText(controller);
        for (const sourceItem of event.sources ?? []) {
          controller.enqueue(
            encodeChunk({
              type: "source-url",
              sourceId: sourceItem.id,
              url: sourceItem.url,
              title: sourceItem.title,
            }),
          );
        }
        controller.enqueue(
          encodeChunk({
            type: "data-sourceDetails",
            data: {
              items: (event.sources ?? []).map((sourceItem) => ({
                id: sourceItem.id,
                title: sourceItem.title,
                url: sourceItem.url,
                section: sourceItem.section ?? "",
                snippet: sourceItem.snippet ?? "",
                sourceCommit: sourceItem.source_commit ?? "",
              })),
            },
          }),
        );
        break;
      case "suggestions":
        controller.enqueue(
          encodeChunk({
            type: "data-suggestions",
            data: { items: event.suggestions ?? [] },
          }),
        );
        break;
      case "support":
        closeText(controller);
        controller.enqueue(
          encodeChunk({
            type: "data-support",
            data: {
              reasonCode: event.reason_code ?? "insufficient_evidence",
              ticketUrl: event.ticket_url ?? "",
              summary: event.summary ?? "",
              text: event.text ?? "",
            },
          }),
        );
        break;
      case "usage":
        if (event.usage) {
          controller.enqueue(
            encodeChunk({
              type: "data-usage",
              data: {
                modelTier: event.usage.model_tier,
                inputTokens: event.usage.input_tokens ?? 0,
                outputTokens: event.usage.output_tokens ?? 0,
                cachedTokens: event.usage.cached_tokens ?? 0,
                cacheHit: event.usage.cache_hit ?? false,
              },
            }),
          );
        }
        break;
      case "message_end":
        closeText(controller);
        controller.enqueue(
          encodeChunk({
            type: "finish",
            finishReason: finishReason(event.finish_reason),
          }),
        );
        controller.enqueue(encodeChunk("[DONE]"));
        finished = true;
        break;
      case "error":
        closeText(controller);
        controller.enqueue(
          encodeChunk({
            type: "error",
            errorText: event.message ?? "پاسخ مستند تکمیل نشد.",
          }),
        );
        controller.enqueue(encodeChunk("[DONE]"));
        finished = true;
        break;
    }
  };

  const consume = (
    block: string,
    controller: ReadableStreamDefaultController<Uint8Array>,
  ) => {
    const data = block
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) {
      return;
    }
    try {
      emit(JSON.parse(data) as BackendEvent, controller);
    } catch {
      controller.enqueue(
        encodeChunk({ type: "error", errorText: "ساختار stream معتبر نیست." }),
      );
      controller.enqueue(encodeChunk("[DONE]"));
      finished = true;
    }
  };

  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      if (finished) {
        controller.close();
        await reader.cancel();
        return;
      }
      const result = await reader.read();
      if (result.done) {
        if (buffer.trim()) {
          consume(buffer, controller);
        }
        if (!finished) {
          closeText(controller);
          controller.enqueue(
            encodeChunk({ type: "error", errorText: "stream ناتمام ماند." }),
          );
          controller.enqueue(encodeChunk("[DONE]"));
        }
        controller.close();
        return;
      }
      buffer += decoder.decode(result.value, { stream: true }).replaceAll("\r\n", "\n");
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        consume(block, controller);
      }
    },
    async cancel(reason) {
      await reader.cancel(reason);
    },
  });
}
