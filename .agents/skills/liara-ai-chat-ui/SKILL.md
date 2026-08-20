---
name: liara-ai-chat-ui
description: Build or review the Liara chat experience with Vercel AI SDK UI and AI Elements on Next.js while a FastAPI service owns RAG, model calls, session policy, and citations. Use for streaming chat, messages, composer, sources, transport, popup/page parity, or AI chat state; do not use for unrelated UI or for moving model secrets into the browser.
---

# Liara AI chat UI

Build one conversation feature rendered in both the popup and full page. The frontend owns interaction state; FastAPI owns knowledge retrieval, model routing, safety, and session truth.

## Required reading

Read `references/chat-protocol.md` before changing transport, message parts, streaming, citations, or session behavior.

## Workflow

1. Inspect installed Next.js, React, Tailwind, shadcn/ui, AI SDK, and AI Elements versions. Current AI Elements prerequisites may be newer than an existing scaffold; resolve versions intentionally.
2. Add only the required AI Elements components. Initial candidates:

```bash
npx ai-elements@latest add message
npx ai-elements@latest add conversation
npx ai-elements@latest add prompt-input
npx ai-elements@latest add sources
npx ai-elements@latest add suggestion
```

3. Use `useChat` with an explicit transport. Route browser traffic through same-origin `/api/chat`; never expose provider credentials client-side.
4. Keep one typed `UIMessage` contract for popup and page. Render text, sources, support escalation, usage/status metadata, and errors from typed parts.
5. Support submit, streaming, Stop, retry when safe, Copy, source opening, session reset, reconnect/failure, rate limits, and escalation.
6. Test with real FastAPI responses. Fixtures are allowed in automated tests, but no production path may return fabricated citations or hard-coded answers.

## Invariants

- Do not render private chain-of-thought. A short user-facing progress label is allowed; hidden reasoning is not.
- Source links come from retrieved document metadata, never from model-written URLs.
- The browser sends the current user action and session identifier; it does not become the authority for the full conversation history.
- Model choice is server-side. Do not expose an unrestricted model picker to end users.
- The answer may stream, but sources and confidence must be attached deterministically and validated before completion.
- Popup and page share the same session when opened in the same browser session.
- Apply maximum input length, disabled/submitted states, abort propagation, and idempotency to prevent duplicate generations.
- Preserve code language labels and Copy behavior provided by the message renderer; add regression tests for Bash, Python, JavaScript, JSON, and YAML.

## Completion evidence

Provide a protocol trace or integration test showing request, stream events, final citations, and session continuation. Verify both surfaces and at least one error, rate-limit, low-confidence, and support-escalation path.
