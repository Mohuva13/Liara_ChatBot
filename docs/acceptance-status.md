# وضعیت معیارهای پذیرش

این فایل بین «پیاده‌شده و تست‌شده در محیط فعلی» و «نیازمند زیرساخت/کلید امن یا release environment» تمایز می‌گذارد. وجود کد به‌تنهایی Done محسوب نمی‌شود.

| حوزه | وضعیت | شاهد فعلی | gate باقی‌مانده |
|---|---|---|---|
| corpus inventory/parser/redaction/chunking | سبز | dry-run واقعی ۱٬۱۴۳ فایل، تست corpus و code fence | secret scan artifact پس از ingestion production |
| versioning/embedding/activation | پیاده‌شده | batch/dimension/idempotency unit tests و migration | integration روی PostgreSQL+Pgvector واقعی و rollback drill |
| hybrid retrieval/evidence/citations | پیاده‌شده | unit/contract و injection tests | Recall/MRR/no-answer روی index واقعی |
| provider AvalAI | سبز محلی | contract، primary/backup failover، quota/auth mapping، circuit/bulkhead و smoke زنده completion ساختاریافته | تکرار smoke با Secret production و quota حساب استقرار |
| session/rate/idempotency/escalation | پیاده‌شده | unit و orchestrator tests | Redis integration، expiry/concurrency/load test |
| Next stream adapter | سبز | Vitest روی SSEهای split، error و typed data | E2E event stream واقعی پشت proxy deployment |
| Page/Popup/RTL/responsive/theme/code actions | سبز محلی | build و browser QA در 320 و 1440، تم light/dark/system، Copy/Download، Escape/focus return | screen-reader matrix و visual regression CI |
| security/privacy | پیاده‌شده | origin/body/citation/injection/internal-hop/CSP/startup validation/secret tests و threat model | dependency audit و external review |
| observability/cost | پیاده‌شده | Prometheus metrics، OTLP traces، usage/cost، token budget، grounded cache و alert runbook | اتصال exporter/dashboard و کالیبراسیون budget در staging |
| deployment | artifact آماده | Dockerfile، liara.json، Compose config و runbook | image build روی daemon، Liara smoke، rollback/restore واقعی |

## حکم release

artifact کد برای release candidate آماده است، اما production release تا عبور gateهای
محیطی مجاز نیست: کلید rotateشده از Secret، Postgres/Pgvector و Redis واقعی،
ingestion فعال، readiness سبز، release eval بالاتر از thresholdهای `spec.md`،
smoke Page/Popup با source معتبر، load و rollback/restore drill.
