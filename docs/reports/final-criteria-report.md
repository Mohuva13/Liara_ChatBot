# گزارش پوشش معیارهای داوری — Liara Documentation Assistant

تاریخ ارزیابی داخلی: ۱۴۰۵/۰۵/۳۰. این گزارش «وجود و آزمون کد» را از «تأیید روی
زیرساخت واقعی» جدا می‌کند. امتیاز نهایی ۳۰۰ توسط داور تعیین می‌شود؛ بدون release
eval و استقرار واقعی، خوداظهاری ۳۰۰/۳۰۰ معتبر نیست.

## جمع‌بندی

| معیار | سقف | وضعیت کد | gate محیطی |
|---|---:|---|---|
| کیفیت و صحت پاسخ‌ها | 80 | پوشش کامل مسیر production | ingest و release eval واقعی |
| UI و تجربه کاربری | 55 | پوشش Page/Popup/RTL/lifecycle | E2E/axe/visual matrix در staging |
| Agentic و Personalization | 50 | پوشش session/intent/level/process/support | human eval سه سطح و چندمرحله‌ای |
| امنیت، پایداری و Monitoring | 50 | پوشش controls و observability | load، dashboard/alerts و external audit |
| استقرار روی لیارا | 40 | artifact و runbook کامل | deployment/rollback واقعی با دسترسی حساب |
| بهینه‌سازی هزینه | 25 | routing/budget/cache/usage/cost | قیمت مدل و budget واقعی staging |

## ۱. کیفیت و صحت پاسخ‌ها — ۸۰

- corpus پاسخ فقط `public/llms/**/*.md` رسمی است؛ canonical URL از `Original
  link` metadata می‌آید و مدل اجازه ساخت URL ندارد.
- ingestion incremental/idempotent و versioned است؛ heading/code-fence-aware،
  content hash/source commit/language metadata، redaction و atomic activation
  دارد.
- retrieval ترکیبی lexical/trigram + exact vector، fusion با RRF، rerank محدود،
  evidence relevance/coverage gate و contradiction-aware fallback دارد.
- هر claim مدل باید source ID معتبر داشته باشد؛ JSON schema و URL/source allowlist
  پس از generation validate می‌شوند. پاسخ مدل که کمبود evidence را داخل یک پاسخ
  ظاهراً معتبر پنهان کند نیز رد می‌شود و source نامرتبط نمایش داده نمی‌شود.
- اگر generation یا repair نامعتبر/موقتاً unavailable باشد، fallback استخراجی فقط
  برای گزاره منفی صریحی فعال می‌شود که همه entityهای نام‌برده‌شده را در همان سند
  رسمی پوشش دهد؛ در غیر این صورت سیستم همچنان fail-closed می‌ماند.
- سؤال کم‌اطلاعات حداکثر یک clarification می‌گیرد؛ تلاش ناموفق بعدی و سؤال مشخصِ
  بدون شاهد مستقیماً Support می‌شوند. پاسخ کوتاه کاربر به clarification با موضوع
  اصلی ترکیب می‌شود، Support برای همان موضوع terminal است، و دو failure صریح همان
  issue مسیر Ticket می‌گیرد.
- simple/complex model routing، مجموعه golden versioned و runner واقعی
  `scripts/run-release-eval.py` برای pass rate/source recall/MRR/latency وجود دارد.

شاهد اصلی: `backend/app/ingestion/`، `backend/app/retrieval/`،
`backend/app/generation/`، `backend/app/services/chat.py` و `evals/datasets/`.

## ۲. طراحی UI و تجربه کاربری — ۵۵

- Next.js App Router، AI SDK UI، AI Elements و shadcn/ui با مالکیت local؛ یک
  `ChatProvider` مشترک برای Popup و Page و session cookie مشترک.
- فارسی RTL، technical content با جهت خودکار/LTR، Markdown امن، syntax/code
  plugin و Copy، source cards، heading/snippet، link و Support CTA.
- welcome/starter، submitted، streaming، Stop، retry، reset، error، no-answer،
  support و suggestionهای حداکثر سه‌تایی.
- Popup با Sheet/focus management/Escape/focus return و full page با composer
  پایدار و scroll-to-bottom.
- semantic landmark، accessible name، live status، keyboard focus، touch target،
  reduced motion و CSS responsive برای 320 تا 1440px.
- security headers و CSP روی frontend؛ adapter فقط stream تایپ‌شده را تبدیل می‌کند.

شاهد اصلی: `frontend/src/features/chat/`، `frontend/src/components/ai-elements/`،
`frontend/src/app/api/chat/route.ts` و `frontend/src/app/globals.css`.

## ۳. Agentic و Personalization — ۵۰

- intentهای deployment/configuration/connection/troubleshooting/comparison/
  plan/account/general-docs و scope بدون مصرف مدل طبقه‌بندی می‌شوند.
- context فقط session-based است: recent turns محدود + factual server summary با
  sliding TTL؛ history کامل browser پذیرفته نمی‌شود.
- سطح دانش از متن و recent turns همان session استنباط و در prompt با
  facts/citations ثابت و سبک بیان متفاوت اعمال می‌شود؛ selector دستی در UI وجود
  ندارد.
- prompt ادامهٔ فرایند چندمرحله‌ای را از next incomplete step الزام می‌کند؛ answer
  شامل verification و قدم بعدی است.
- clarification فقط در query کم‌اطلاعات؛ repeated failure per issue و تغییر topic
  شمارنده را جدا نگه می‌دارد؛ بعد از دومین failure Ticket primary می‌شود.
- reset/rotation session، idempotency و ادامه مکالمه در Popup/Page مشترک است.

## ۴. امنیت، پایداری و Monitoring — ۵۰

- Secretها server-only و production startup برای secret/config مفقود fail می‌شود؛
  `.env*` واقعی ignored و secret scanner موجود است.
- Redis rate limit توزیع‌شده burst+sustained بر session+IP hash+route با
  `Retry-After`؛ idempotency مانع generation تکراری می‌شود.
- same-origin adapter، CORS allowlist، request byte/character limit، content type،
  Secure/HttpOnly/SameSite cookie، CSP، frame/referrer/permission headers.
- hop خصوصی Next→FastAPI با token ثابت‌زمان؛ raw IP فقط در Next hash می‌شود.
- provider timeout، retry با jitter، عدم retry credential منقضی روی همان key،
  primary/backup failover، circuit breaker، bulkhead/queue timeout و stream-safe
  buffering دارد.
- generation ساختاریافته از completion غیرstream با JSON mode استفاده می‌کند؛ چون
  پاسخ پیش از نمایش باید به‌طور کامل grounding-validate شود. UI متن تأییدشده را
  chunk می‌کند و به streaming ناسازگار provider وابسته نیست.
- structured JSON logs بدون user text/prompt/chunk/PII؛ correlation ID، route،
  latency، outcome، model، token، cache، provider و corpus version ثبت می‌شود.
- Prometheus endpoint حفاظت‌شده و OpenTelemetry OTLP exporter اختیاری؛ metrics
  request/error/latency، retrieval، TTFT، outcomes، token، cache/provider و rate
  limit را پوشش می‌دهد. thresholdهای alert در deployment runbook تعریف شده‌اند.

## ۵. استقرار روی زیرساخت لیارا — ۴۰

- backend Docker non-root با lockfile، healthcheck و graceful provider shutdown؛
  frontend Next.js دارای `liara.json` و production build است.
- topology خصوصی Next/FastAPI/PostgreSQL/Pgvector/Redis، env matrix، migration،
  ingestion job، smoke، eval، monitoring، backup، restore و rollback در
  `docs/runbooks/deployment.md` مستند شده است.
- `/health/live` سبک و `/health/ready` شامل Postgres/Redis/active corpus/provider
  config است. HNSW فرض نشده و exact baseline است.
- تنها gate باقیمانده اقدام خارجی است: ساخت resource و release واقعی در حساب
  لیارا، که بدون credential/مجوز حساب قابل انجام نیست.

## ۶. بهینه‌سازی هزینه — ۲۵

- مسیر deterministic/no-model برای out-of-scope/policy/clarification؛ small برای
  پرسش مستقیم و large فقط برای ambiguity/multi-document/diagnosis.
- سقف evidence/context/output، history bounded، pre-call input token budget،
  concurrency limit و retry budget configurable.
- Redis grounded-response cache با key شامل normalized query، intent، corpus
  versions، policy version، locale و knowledge level؛ فقط session-independent و
  non-failure-sensitive cache می‌شود و hit دوباره grounding validation می‌گیرد.
- usage واقعی provider شامل input/output/cached tokens و primary/backup است؛ cost
  estimate با قیمت‌های environment-configured محاسبه و در event/log ثبت می‌شود.
- cache hit ratio، token/model/provider metrics و cost alert برای dashboard تعریف
  شده‌اند.

## آزمون و حکم release

گیت محلی شامل Ruff، format check، Mypy strict، Pytest، ESLint، TypeScript، Vitest،
Next production build، secret scan، corpus inventory و dataset validation است.
در آخرین اجرای ثبت‌شده: ۷۹ تست backend و ۲۰ تست frontend پاس شدند، scope accuracy
روی ۸ case برابر ۱٫۰ بود، build تولیدی موفق شد، secret scan پاک بود و audit
وابستگی‌های production در npm و PyPI آسیب‌پذیری شناخته‌شده‌ای گزارش نکرد. QA
مرورگر production در عرض ۳۲۰ و ۱۴۴۰ بدون overflow بود و Escape/focus-return
Popup نیز پاس شد.

موارد زیر کدنویسی نیستند و باید در staging واقعی اجرا و artifact آن‌ها نگهداری
شود: provider smoke با key چرخانده‌شده، PostgreSQL/Pgvector و Redis integration،
release RAG eval، E2E browser/axe/visual، load/p95، dependency audit، dashboard
alert fire test و backup/restore/rollback drill. تا آن زمان وضعیت «release
candidate» است، نه «production verified».
