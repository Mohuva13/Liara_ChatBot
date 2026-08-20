import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { isSameOriginRequest } from "@/lib/http/same-origin";

const SESSION_COOKIE = "liara_assistant_session";

function internalBaseUrl(): string | null {
  const configured = process.env.API_INTERNAL_BASE_URL?.trim();
  return configured ? configured.replace(/\/$/, "") : null;
}

export async function DELETE(request: Request) {
  if (!isSameOriginRequest(request)) {
    return NextResponse.json(
      { error: { code: "invalid_origin", message: "مبدأ درخواست معتبر نیست." } },
      { status: 403 },
    );
  }
  const cookieStore = await cookies();
  const sessionId = cookieStore.get(SESSION_COOKIE)?.value;
  const baseUrl = internalBaseUrl();
  if (sessionId && baseUrl) {
    try {
      await fetch(`${baseUrl}/v1/sessions/${encodeURIComponent(sessionId)}`, {
        method: "DELETE",
        cache: "no-store",
        signal: request.signal,
      });
    } catch {
      // Reset remains local and recoverable when the backend is temporarily down.
    }
  }
  const response = new NextResponse(null, { status: 204 });
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
