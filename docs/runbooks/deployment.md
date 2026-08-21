# راهنمای جامع استقرار Production روی لیارا

این runbook برای انتشار دو برنامهٔ مستقل `frontend` و `backend` به‌همراه
PostgreSQL/Pgvector و Redis نوشته شده است. هیچ مقدار Secret نباید در Git،
`liara.json`، Docker image، log یا history شل قرار گیرد.

## ۱. معماری مقصد

```text
Internet -> Next.js frontend -> private HTTP -> FastAPI backend
                                      |-> PostgreSQL + Pgvector
                                      |-> Redis
                                      |-> AvalAI primary / backup
```

- فقط frontend عمومی است. backend، PostgreSQL و Redis در یک شبکهٔ خصوصی مشترک
  قرار می‌گیرند.
- frontend و backend با `API_INTERNAL_TOKEN` مشترک احراز می‌شوند؛ این مقدار فقط
  server-side است و نام آن نباید با `NEXT_PUBLIC_` شروع شود.
- browser هرگز provider key، connection string یا history قابل‌اعتماد تولید
  نمی‌کند.
- backend بدون Redis/PostgreSQL/corpus فعال/provider سالم، روی `/health/ready`
  پاسخ `503` می‌دهد و پاسخ ساختگی تولید نمی‌کند.

مستندات رسمی لیارا تأکید می‌کند سرویس‌های مرتبط باید هنگام ساخت در یک شبکهٔ
خصوصی باشند و شبکه بعداً قابل تغییر نیست: [شبکه خصوصی](https://docs.liara.ir/paas/details/private-network/).

## ۲. پیش‌نیاز و نام‌گذاری

در Console لیارا یک شبکه مانند `liara-assistant-prod` و این منابع را بسازید:

1. PostgreSQL دارای افزونه Pgvector؛ دسترسی عمومی در حالت عادی خاموش.
2. Redis؛ دسترسی عمومی خاموش.
3. برنامه Docker برای backend با پورت `8000`.
4. برنامه Next.js برای frontend با پورت `3000`.

انتخاب plan باید پس از load test انجام شود. baseline پیشنهادی برای staging یک
نمونه backend و frontend و کوچک‌ترین plan دیتابیس قابل قبول است؛ production
باید با p95، memory و connection count واقعی resize شود. Liara برای Docker فقط
یک HTTP web port را expose می‌کند: [استقرار Docker](https://docs.liara.ir/paas/docker/how-tos/deploy-app/).

## ۳. Secret rotation قبل از انتشار

هر کلیدی که در chat، issue، screenshot یا log دیده شده است افشاشده محسوب می‌شود:

1. آن را در provider revoke کنید.
2. دو کلید جدید و مستقل با quota مناسب بسازید: primary و backup.
3. برای frontend/backend یک `API_INTERNAL_TOKEN` تصادفی و حداقل ۳۲-byte بسازید.
4. برای metrics یک `METRICS_BEARER_TOKEN` مستقل بسازید.
5. مقادیر را فقط از Console > Environment/Secrets وارد کنید.

کلید backup نباید clone همان credential باشد؛ در غیر این صورت اتمام quota یا
لغو credential هر دو مسیر را هم‌زمان از کار می‌اندازد.

## ۴. ماتریس متغیرهای محیطی

### Backend — الزامی

| متغیر | مقدار/منبع |
|---|---|
| `APP_ENV` | `production` |
| `WEB_ORIGIN` | URL عمومی دقیق frontend، بدون wildcard |
| `API_INTERNAL_TOKEN` | Secret مشترک با frontend |
| `DATABASE_URL` | connection string خصوصی PostgreSQL از Console |
| `REDIS_URL` | connection string خصوصی Redis از Console |
| `LLM_PROVIDER` | `openai-compatible` |
| `LLM_BASE_URL` | endpoint سازگار provider |
| `LLM_API_KEY` | Secret primary جدید |
| `LLM_BACKUP_BASE_URL` | endpoint backup؛ می‌تواند برابر primary باشد |
| `LLM_BACKUP_API_KEY` | Secret backup مستقل |
| `LLM_SMALL_MODEL` | model تأییدشده در smoke test |
| `LLM_LARGE_MODEL` | model تأییدشده در smoke test |
| `EMBEDDING_BASE_URL` | endpoint embedding |
| `EMBEDDING_API_KEY` | Secret embedding primary |
| `EMBEDDING_BACKUP_BASE_URL` | endpoint embedding backup |
| `EMBEDDING_BACKUP_API_KEY` | Secret embedding backup |
| `EMBEDDING_MODEL` | model تأییدشده |
| `EMBEDDING_DIMENSIONS` | dimension واقعی پاسخ provider و migration |
| `EMBEDDING_BATCH_SIZE` | baseline برابر `16`؛ افزایش فقط پس از benchmark provider |
| `EMBEDDING_REQUEST_TIMEOUT_SECONDS` | timeout مستقل embedding؛ baseline برابر `120` |
| `METRICS_BEARER_TOKEN` | Secret مستقل برای scrape کردن `/metrics` |

### Backend — policy/cost tuning

`SESSION_TTL_SECONDS=7200`، `SESSION_MAX_TURNS=24`،
`RATE_LIMIT_ANONYMOUS_PER_MINUTE=10`،
`RATE_LIMIT_ANONYMOUS_PER_HOUR=60`، `RESPONSE_CACHE_TTL_SECONDS=900`،
`MAX_PROVIDER_INPUT_TOKENS=16000`، `MAX_OUTPUT_TOKENS_SMALL=700` و
`MAX_OUTPUT_TOKENS_LARGE=1200` baselineهای versioned هستند. تغییر آن‌ها باید با
eval و cost report همراه باشد.

چهار متغیر `LLM_SMALL_INPUT_USD_PER_MILLION`،
`LLM_SMALL_OUTPUT_USD_PER_MILLION`، `LLM_LARGE_INPUT_USD_PER_MILLION` و
`LLM_LARGE_OUTPUT_USD_PER_MILLION` باید با قیمت قراردادی همان provider مقدار
غیرصفر داشته باشند؛ production با قیمت صفر start نمی‌شود.

Failover با `PROVIDER_CIRCUIT_FAILURE_THRESHOLD=3`،
`PROVIDER_CIRCUIT_RESET_SECONDS=30`، `PROVIDER_CONCURRENCY_LIMIT=8` و
`PROVIDER_QUEUE_TIMEOUT_SECONDS=2` کنترل می‌شود. switch فقط برای auth/quota،
429، timeout و 5xx است؛ درخواست نامعتبر روی backup تکرار نمی‌شود.

### Frontend — الزامی و server-only

| متغیر | مقدار |
|---|---|
| `NODE_ENV` | `production` |
| `API_INTERNAL_BASE_URL` | آدرس خصوصی backend، مانند `http://<backend-id>:8000` |
| `API_INTERNAL_TOKEN` | همان Secret backend |

هیچ `LLM_*`، `EMBEDDING_*`، `DATABASE_URL` یا `REDIS_URL` در frontend تنظیم
نشود. متغیرهای Secret را داخل `next.config.ts env` قرار ندهید، چون ممکن است در
bundle قرار گیرند. راهنمای رسمی: [متغیرهای محیطی Next.js](https://docs.liara.ir/paas/nextjs/how-tos/set-envs/).

## ۵. آماده‌سازی دیتابیس و corpus

1. از مسیر اتصال خصوصی PostgreSQL استفاده کنید.
2. migrationهای `backend/migrations/` را به ترتیب اجرا کنید. ingestion CLI نیز
   migrationها را قبل از ingest اعمال می‌کند.
3. repository رسمی docs و همین repository را در runner امن CI یا workstation
   checkout کنید؛ runtime backend به mount مستندات نیاز ندارد.
4. متغیرهای backend را به runner تزریق و ingestion را اجرا کنید:

```bash
cd backend
.venv/bin/python -m app.ingestion.cli --activate
```

Ingestion تعداد فایل‌ها را در هر اجرا محاسبه می‌کند، canonical URL را از
`Original link` می‌گیرد، credential examples را redact می‌کند، code block را
نمی‌شکند و نسخه را فقط پس از embedding کامل atomic فعال می‌کند. HNSW ساخته
نمی‌شود؛ سند PostgreSQL لیارا صریحاً نبود پشتیبانی HNSW را ذکر می‌کند و انتخاب
فعلی exact search است. IVFFlat فقط پس از benchmark مجاز است.

Embedding هر batch در نسخهٔ غیرفعال corpus checkpoint می‌شود. شکست provider یا
قطع runner نسخه را active نمی‌کند و اجرای بعدی فقط chunkهای ناقص را resume
می‌کند؛ تغییر model یا dimensions هنگام resume عمداً fail-closed است.

## ۶. انتشار برنامه‌ها

### Backend

context انتشار باید پوشه `backend/` باشد. `Dockerfile` با user غیر-root اجرا
می‌شود، dependencyهای lockشده را نصب می‌کند و health check دارد. از Console،
GitHub deployment یا CLI رسمی استفاده کنید؛ اگر GitHub deployment دارید فیلدهای
`app` و `platform` را به `liara.json` اضافه نکنید، چون طبق مستند رسمی در این روش
کاربرد ندارند. مرجع: [liara.json](https://docs.liara.ir/paas/liarajson/).

پس از انتشار backend، قبل از frontend این سه تست باید سبز باشند:

```bash
curl --fail https://BACKEND_URL/health/live
curl --fail https://BACKEND_URL/health/ready
curl --fail -H "Authorization: Bearer $METRICS_BEARER_TOKEN" \
  https://BACKEND_URL/metrics
```

### Frontend

context انتشار `frontend/` و platform برابر Next.js است. لیارا در deployment
Next.js، install و build را اجرا می‌کند: [شروع سریع Next.js](https://docs.liara.ir/paas/nextjs/quick-start/).
`API_INTERNAL_BASE_URL` باید hostname و port خصوصی backend باشد. بعد از تغییر
Environment برنامه را restart/redeploy کنید.

## ۷. smoke، eval و پذیرش release

ابتدا provider را با Secret چرخانده‌شده و بدون قرار دادن کلید در argv/history
بررسی کنید:

```bash
cd backend
LLM_SMALL_MODEL=<verified-model> EMBEDDING_MODEL=<verified-model> \
  .venv/bin/python scripts/provider_smoke.py
```

اسکریپت در terminal مقدار را با prompt مخفی می‌گیرد. برای CI مقدار باید از Secret
store به environment تزریق شود.

سپس release eval واقعی را روی backend آماده اجرا کنید:

```bash
EVAL_BASE_URL=https://BACKEND_URL \
  backend/.venv/bin/python scripts/run-release-eval.py > release-eval.json
```

شرایط release:

- `/health/ready` سبز؛
- pass rate حداقل ۹۰٪، expected source recall حداقل ۹۰٪ و MRR حداقل ۰٫۷۵؛
- پاسخ فنی بدون source یا source خارج از `docs.liara.ir` برابر صفر؛
- Page و Popup روی 320/375/768/1024/1440px، keyboard، Stop، Retry، reset، code
  copy، source و Support تست شوند؛
- secret scan، lint، type-check، unit/integration، build و dependency audit سبز؛
- p95 و cost budget در staging تأیید شود.

## ۸. مانیتورینگ و alert

`/metrics` با bearer token این سیگنال‌های bounded و بدون متن کاربر را ارائه می‌دهد:

- `liara_http_requests_total` بر اساس route/status؛
- مجموع latency هر route برای محاسبه average/rate؛
- `liara_chat_outcomes_total` بر اساس outcome/model/cache/provider؛
- `liara_provider_tokens_total` برای ورودی/خروجی و model tier.

JSON log شامل correlation ID، route، status، latency، outcome، model tier، token،
cache status، provider primary/backup و corpus version است؛ prompt، chunk و متن
کامل کاربر log نمی‌شود. alertهای staging/production:

| Alert | شرط اولیه |
|---|---|
| readiness | سه check پیاپی ناموفق |
| error spike | 5xx بیش از ۵٪ در ۵ دقیقه |
| provider | provider error بیش از ۳ رخداد یا circuit open |
| latency | p95 TTFT بیش از ۷s یا پاسخ کامل بیش از ۱۵s |
| grounding | `grounding_failed` یا citation failure بیشتر از baseline |
| no-answer | رشد بیش از ۳ واحد درصد نسبت به release قبل |
| cost | token/day یا large-route share بیشتر از budget |
| backup | هر استفاده از backup؛ هشدار rotation/quota primary |

## ۹. Backup، rollback و disaster recovery

- برنامه: از تاریخچه deployment به release قبلی برگردید و health/smoke را تکرار
  کنید.
- corpus: نسخه جدید را حذف نکنید؛ نسخه قبلی را در transaction active و eval را
  دوباره اجرا کنید.
- PostgreSQL: backup زمان‌بندی‌شده و restore drill فصلی؛ RPO/RTO قبل از release
  ثبت شود. restore روی محیط جدا و count/version/hash corpus کنترل شود.
- Redis منبع حقیقت corpus نیست، اما session/rate/idempotency را نگه می‌دارد؛
  persistence و HA متناسب plan فعال شود.
- provider: بعد از هشدار backup، quota/credential primary را اصلاح و smoke کنید؛
  هر دو کلید را هم‌زمان rotate نکنید.

## ۱۰. checklist نهایی

- [ ] Secret افشاشده revoke و دو کلید مستقل ایجاد شده است.
- [ ] هر چهار resource در شبکه خصوصی مشترک‌اند و DB/Redis عمومی نیستند.
- [ ] migration و ingestion atomic موفق و corpus version ثبت شده است.
- [ ] backend ready، metrics و provider smoke سبز است.
- [ ] release eval report ذخیره و thresholdها پاس شده‌اند.
- [ ] frontend build و E2E Page/Popup سبز است.
- [ ] alertها، owner/on-call، RPO/RTO و rollback trigger مشخص‌اند.
- [ ] backup restore و rollback corpus/release تمرین شده است.

هر critical hallucination، source جعلی، secret leakage، readiness ناپایدار،
regression بیش از tolerance یا عبور هزینه از budget، trigger توقف release یا
rollback است.
