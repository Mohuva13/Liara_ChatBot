import { createHash, randomUUID } from "node:crypto";

import type { UIMessage } from "ai";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { mapBackendStream } from "@/features/chat/transport/backend-stream";
import { isSameOriginRequest } from "@/lib/http/same-origin";

const SESSION_COOKIE = "liara_assistant_session";
const MAX_REQUEST_BYTES = 64 * 1024;

type ClientChatBody = {
  messages?: unknown;
  surface?: unknown;
  knowledgeLevel?: unknown;
};

type SessionPayload = {
  session_id: string;
  expires_in_seconds: number;
};

function internalBaseUrl(): string | null {
  const configured = process.env.API_INTERNAL_BASE_URL?.trim();
  return configured ? configured.replace(/\/$/, "") : null;
}

function internalHeaders(): Record<string, string> {
  const token = process.env.API_INTERNAL_TOKEN?.trim();
  return token ? { "x-internal-token": token } : {};
}

function clientIdentity(request: Request): string {
  const address =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  const salt = process.env.API_INTERNAL_TOKEN?.trim() ?? "local-development";
  return createHash("sha256").update(`${salt}:${address}`).digest("hex").slice(0, 32);
}

function latestUserMessage(messages: unknown): UIMessage | null {
  if (!Array.isArray(messages)) {
    return null;
  }
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const candidate = messages[index] as Partial<UIMessage>;
    if (
      candidate.role === "user" &&
      typeof candidate.id === "string" &&
      Array.isArray(candidate.parts)
    ) {
      return candidate as UIMessage;
    }
  }
  return null;
}

function textFromMessage(message: UIMessage): string {
  return message.parts
    .filter((part) => part.type === "text")
    .map((part) => part.text)
    .join("")
    .trim();
}

function publicError(status: number, code: string, message: string) {
  return NextResponse.json({ error: { code, message } }, { status });
}

async function createSession(baseUrl: string): Promise<SessionPayload | null> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/v1/sessions`, {
      method: "POST",
      headers: { "content-type": "application/json", ...internalHeaders() },
      cache: "no-store",
    });
  } catch {
    return null;
  }
  if (!response.ok) {
    return null;
  }
  const payload: unknown = await response.json();
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("session_id" in payload) ||
    !("expires_in_seconds" in payload) ||
    typeof payload.session_id !== "string" ||
    typeof payload.expires_in_seconds !== "number"
  ) {
    return null;
  }
  return payload as SessionPayload;
}

export async function POST(request: Request) {
  if (!isSameOriginRequest(request)) {
    return publicError(403, "invalid_origin", "مبدأ درخواست معتبر نیست.");
  }
  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().startsWith("application/json")) {
    return publicError(415, "unsupported_media_type", "نوع درخواست معتبر نیست.");
  }
  const contentLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(contentLength) && contentLength > MAX_REQUEST_BYTES) {
    return publicError(413, "request_too_large", "حجم درخواست بیش از حد مجاز است.");
  }

  const rawBody = await request.arrayBuffer();
  if (rawBody.byteLength > MAX_REQUEST_BYTES) {
    return publicError(413, "request_too_large", "حجم درخواست بیش از حد مجاز است.");
  }

  const baseUrl = internalBaseUrl();
  if (baseUrl === null) {
    return publicError(
      503,
      "backend_not_configured",
      "ارتباط داخلی دستیار پیکربندی نشده است.",
    );
  }

  let body: ClientChatBody;
  try {
    body = JSON.parse(new TextDecoder().decode(rawBody)) as ClientChatBody;
  } catch {
    return publicError(400, "invalid_json", "ساختار درخواست معتبر نیست.");
  }

  const message = latestUserMessage(body.messages);
  const text = message ? textFromMessage(message) : "";
  if (message === null || text.length === 0) {
    return publicError(422, "invalid_message", "پیام کاربر معتبر نیست.");
  }

  const cookieStore = await cookies();
  let sessionId = cookieStore.get(SESSION_COOKIE)?.value;
  let createdSession: SessionPayload | null = null;
  if (!sessionId) {
    createdSession = await createSession(baseUrl);
    if (createdSession === null) {
      return publicError(
        503,
        "session_unavailable",
        "نشست گفتگو موقتاً در دسترس نیست.",
      );
    }
    sessionId = createdSession.session_id;
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${baseUrl}/v1/chat/stream`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        accept: "text/event-stream",
        "x-request-id": randomUUID(),
        "x-client-id": clientIdentity(request),
        ...internalHeaders(),
      },
      body: JSON.stringify({
        protocol_version: "1",
        session_id: sessionId,
        message_id: message.id,
        text,
        surface: body.surface === "popup" ? "popup" : "page",
        locale: "fa-IR",
        knowledge_level:
          body.knowledgeLevel === "beginner" ||
          body.knowledgeLevel === "advanced"
            ? body.knowledgeLevel
            : "intermediate",
      }),
      cache: "no-store",
      signal: request.signal,
    });
  } catch {
    return publicError(
      503,
      "backend_unavailable",
      "سرویس پاسخ‌گویی موقتاً در دسترس نیست.",
    );
  }

  if (!upstream.ok || upstream.body === null) {
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: {
        "content-type":
          upstream.headers.get("content-type") ??
          "application/json; charset=utf-8",
        "cache-control": "no-store",
        "retry-after": upstream.headers.get("retry-after") ?? "",
        "x-request-id": upstream.headers.get("x-request-id") ?? randomUUID(),
      },
    });
  }

  const response = new NextResponse(mapBackendStream(upstream.body), {
    status: upstream.status,
    headers: {
      "content-type": "text/event-stream",
      "cache-control": "no-cache, no-store",
      "x-accel-buffering": "no",
      "x-vercel-ai-ui-message-stream": "v1",
      "x-request-id": upstream.headers.get("x-request-id") ?? randomUUID(),
    },
  });
  if (createdSession !== null) {
    response.cookies.set({
      name: SESSION_COOKIE,
      value: createdSession.session_id,
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: createdSession.expires_in_seconds,
    });
  }
  return response;
}
