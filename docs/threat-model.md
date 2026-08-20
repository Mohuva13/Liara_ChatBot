# Threat model

| مرز | تهدید اصلی | کنترل فعلی |
|---|---|---|
| Browser → Next adapter | forged history، CSRF، oversized input | فقط آخرین user message، Origin/forwarded-origin validation، byte limit، HttpOnly/SameSite cookie |
| Next → FastAPI | دسترسی مستقیم یا replay | شبکه خصوصی، `API_INTERNAL_TOKEN` با compare ثابت‌زمان، session opaque، idempotency و request ID |
| Query/corpus → model | prompt injection و secret leakage | corpus به‌عنوان دادهٔ untrusted، redaction پیش از embedding، خروجی JSON validateشده |
| Model → user | hallucinated claim/URL | evidence gate، source ID allowlist، URL فقط از server metadata، یک repair محدود |
| Redis | session mix-up، abuse، outage | key namespace، sliding TTL، bounded turns، distributed rate limit، fail closed |
| PostgreSQL/Pgvector | stale/partial index | versioned corpus، atomic activation، no activation with missing vectors |
| Provider | key exposure، timeout، quota، cost spike | server-only primary/backup، timeout، jitter retry، circuit/bulkhead، token/model routing، usage/cost event |
| Logs | PII/prompt disclosure | structured metadata only؛ متن user، prompt و chunk log نمی‌شوند |

ریسک‌های باقی‌ماندهٔ محیطی پیش از production: dependency audit در CI، load test،
restore drill واقعی و کالیبراسیون release eval روی provider و corpus نهایی.
