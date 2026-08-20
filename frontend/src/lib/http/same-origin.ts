function normalizedOrigin(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return null;
    }
    return url.origin;
  } catch {
    return null;
  }
}

export function isSameOriginRequest(request: Request): boolean {
  const suppliedOrigin = normalizedOrigin(request.headers.get("origin"));
  if (suppliedOrigin === null) {
    return request.headers.get("origin") === null;
  }

  const candidates = new Set<string>();
  const requestOrigin = normalizedOrigin(request.url);
  if (requestOrigin) {
    candidates.add(requestOrigin);
  }

  const configuredOrigin = normalizedOrigin(process.env.WEB_ORIGIN);
  if (configuredOrigin) {
    candidates.add(configuredOrigin);
  }

  const forwardedHost = request.headers.get("x-forwarded-host");
  const forwardedProtocol = request.headers.get("x-forwarded-proto") ?? "https";
  const forwardedOrigin = normalizedOrigin(
    forwardedHost ? `${forwardedProtocol}://${forwardedHost}` : null,
  );
  if (forwardedOrigin) {
    candidates.add(forwardedOrigin);
  }

  const host = request.headers.get("host");
  const directOrigin = normalizedOrigin(
    host ? `${new URL(request.url).protocol}//${host}` : null,
  );
  if (directOrigin) {
    candidates.add(directOrigin);
  }

  return candidates.has(suppliedOrigin);
}
