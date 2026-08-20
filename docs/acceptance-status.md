# وضعیت معیارهای پذیرش

این فایل بین «پیاده‌شده و تست‌شده در محیط فعلی» و «نیازمند زیرساخت/کلید امن یا release environment» تمایز می‌گذارد. وجود کد به‌تنهایی Done محسوب نمی‌شود.

| حوزه | وضعیت | شاهد فعلی | gate باقی‌مانده |
|---|---|---|---|
| corpus inventory/parser/redaction/chunking | سبز | dry-run واقعی ۱٬۱۴۳ فایل، تست corpus و code fence | secret scan artifact پس از ingestion production |
| versioning/embedding/activation | پیاده‌شده | batch/dimension/idempotency unit tests و migration | integration روی PostgreSQL+Pgvector واقعی و rollback drill |
| hybrid retrieval/evidence/citations | پیاده‌شده | unit/contract و injection tests | Recall/MRR/no-answer روی index واقعی |
| provider AvalAI | پیاده‌شده | contract test با transport ضبط‌شده، error mapping و jitter retry | smoke زنده با کلید rotateشده و تأیید model names/quota |
| session/rate/idempotency/escalation | پیاده‌شده | unit و orchestrator tests | Redis integration، expiry/concurrency/load test |
| Next stream adapter | سبز | Vitest روی SSEهای split و typed data | E2E stream واقعی پشت proxy deployment |
| Page/Popup/RTL/responsive | سبز محلی | build و browser QA در 320 و 1440، Escape/focus return | screen-reader matrix و visual regression CI |
| security/privacy | پیاده‌شده | origin/body/citation/injection/secret tests و threat model | private-hop authentication، dependency audit و external review |
| observability/cost | پایه موجود | request/outcome JSON metadata و usage events | exporter/dashboard/alert در محیط staging |
| deployment | artifact آماده | Dockerfile، liara.json، Compose config و runbook | image build روی daemon، Liara smoke، rollback/restore واقعی |

## حکم release

نسخه برای توسعه و نمایش UI قابل اجراست، اما production release هنوز مجاز نیست. شرط عبور: کلید rotateشده از Secret، Postgres/Pgvector و Redis واقعی، ingestion فعال، readiness سبز، release eval بالاتر از thresholdهای `spec.md` و smoke Page/Popup با source معتبر.
