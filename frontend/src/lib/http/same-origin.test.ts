import { afterEach, describe, expect, it } from "vitest";

import { isSameOriginRequest } from "./same-origin";

afterEach(() => {
  delete process.env.WEB_ORIGIN;
});

describe("isSameOriginRequest", () => {
  it("accepts the direct request origin", () => {
    const request = new Request("http://127.0.0.1:3000/api/chat", {
      headers: { origin: "http://127.0.0.1:3000" },
    });

    expect(isSameOriginRequest(request)).toBe(true);
  });

  it("accepts the trusted forwarded public origin", () => {
    const request = new Request("http://next:3000/api/chat", {
      headers: {
        origin: "https://assistant.example.com",
        "x-forwarded-host": "assistant.example.com",
        "x-forwarded-proto": "https",
      },
    });

    expect(isSameOriginRequest(request)).toBe(true);
  });

  it("rejects a cross-origin request", () => {
    const request = new Request("https://assistant.example.com/api/chat", {
      headers: { origin: "https://attacker.example" },
    });

    expect(isSameOriginRequest(request)).toBe(false);
  });

  it("rejects a malformed Origin header", () => {
    const request = new Request("https://assistant.example.com/api/chat", {
      headers: { origin: "not a URL" },
    });

    expect(isSameOriginRequest(request)).toBe(false);
  });
});
