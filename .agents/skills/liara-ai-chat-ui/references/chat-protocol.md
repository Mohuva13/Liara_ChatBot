# Next.js–FastAPI chat protocol

## Official UI sources

- AI Elements setup: <https://elements.ai-sdk.dev/docs/setup>
- Message: <https://elements.ai-sdk.dev/components/message>
- Conversation: <https://elements.ai-sdk.dev/components/conversation>
- Prompt Input: <https://elements.ai-sdk.dev/components/prompt-input>
- Sources: <https://elements.ai-sdk.dev/components/sources>
- AI SDK `useChat`: <https://ai-sdk.dev/docs/reference/ai-sdk-ui/use-chat>
- AI SDK transport: <https://ai-sdk.dev/docs/ai-sdk-ui/transport>

Check these pages at implementation time. Their version requirements and APIs can change.

## Service boundary

```text
Browser useChat
  -> same-origin Next.js /api/chat adapter
  -> private FastAPI /v1/chat/stream
  -> session + intent + retrieval + confidence + model router
  -> provider API
  -> validated stream events
  -> Next adapter emits AI SDK-compatible UI message stream
```

The Next.js route is a thin protocol adapter and security boundary, not a second RAG implementation. FastAPI remains the backend of record.

## Request envelope

The adapter sends a versioned request such as:

```json
{
  "protocol_version": "1",
  "session_id": "opaque-server-issued-id",
  "message_id": "client-generated-idempotency-key",
  "text": "متن کاربر",
  "surface": "page",
  "locale": "fa-IR"
}
```

Do not accept `system` messages or authoritative history from the browser. Validate length, Unicode, content type, origin, and idempotency.

## Stream events

FastAPI should emit typed SSE or NDJSON events that the Next adapter maps to AI SDK UI parts:

| Event | Required data | UI behavior |
|---|---|---|
| `message_start` | response ID, session ID | mark submitted/streaming |
| `status` | safe short phase label | optional progress text, no chain-of-thought |
| `text_delta` | answer delta | append text |
| `sources` | validated canonical sources | render separate Sources/card region |
| `suggestions` | grounded next actions | render suggestion controls |
| `support` | reason code, ticket URL, summary | render escalation card |
| `usage` | model tier, input/output token counts, cache flag | telemetry/admin metadata, not raw provider secrets |
| `message_end` | finish reason, groundedness outcome | ready state |
| `error` | stable public error code/message, retryable | accessible error state |

Do not send raw prompts, retrieved private metadata, stack traces, provider responses, or internal confidence thresholds to the browser.

## Source schema

```json
{
  "id": "stable-document-or-chunk-id",
  "title": "عنوان سند",
  "url": "https://docs.liara.ir/.../",
  "section": "عنوان بخش",
  "snippet": "گزیده کوتاه و دقیق",
  "updated_at": "source revision when available"
}
```

URLs are constructed from ingestion metadata and allowlisted to official Liara documentation domains. The model never invents or rewrites them.

## Session behavior

- FastAPI issues an opaque session ID stored in a Secure, HttpOnly, SameSite cookie by the Next adapter where possible.
- Redis stores bounded active-session state with a sliding TTL. No long-term personalization is implied.
- A session reset deletes active state and starts a new opaque session.
- Context uses recent turns plus a server-produced factual summary. Never trust a client-edited assistant message as prior truth.
- Reopening the popup or navigating to the page in the same browser session resumes the same active conversation.

## Error mapping

- `400 invalid_input`: preserve input, show correction.
- `409 duplicate_in_progress`: attach to the existing stream or avoid a duplicate request.
- `429 rate_limited`: show retry-after without automatic retry storms.
- `503 provider_unavailable`: safe retry action; do not lose conversation.
- `504 generation_timeout`: explain timeout and allow one controlled retry.
- `grounding_failed`: no answer text; show support or clarification depending on policy.

## Testing contract

- Contract test the FastAPI event schema and Next adapter mapping.
- Verify abort propagates from `useChat.stop()` to the upstream request.
- Verify citation cards are impossible without source metadata.
- Verify reconnect or failure never duplicates an assistant response.
- Verify code rendering and Copy behavior on both popup and page.
