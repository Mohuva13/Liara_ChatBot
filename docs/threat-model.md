# Threat model

| مرز | تهدید اصلی | کنترل فعلی |
|---|---|---|
| Browser → Next adapter | forged history، CSRF، oversized input | فقط آخرین user message، Origin/forwarded-origin validation، byte limit، HttpOnly/SameSite cookie |
| Next → FastAPI | دسترسی مستقیم یا replay | session opaque، idempotency reservation، request ID، private deployment boundary |
| Query/corpus → model | prompt injection و secret leakage | corpus به‌عنوان دادهٔ untrusted، redaction پیش از embedding، خروجی JSON validateشده |
| Model → user | hallucinated claim/URL | evidence gate، source ID allowlist، URL فقط از server metadata، یک repair محدود |
| Redis | session mix-up، abuse، outage | key namespace، sliding TTL، bounded turns، distributed rate limit، fail closed |
| PostgreSQL/Pgvector | stale/partial index | versioned corpus، atomic activation، no activation with missing vectors |
| Provider | key exposure، timeout، cost spike | server-only Secret، timeout، bounded jitter retry، token/model routing، usage event |
| Logs | PII/prompt disclosure | structured metadata only؛ متن user، prompt و chunk log نمی‌شوند |

ریسک‌های باقیمانده پیش از production: احراز هویت hop خصوصی Next→FastAPI، dependency audit در CI، load test، restore drill واقعی و کالیبراسیون eval روی provider نهایی.
