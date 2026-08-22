# دستیار مستندات لیارا

یک دستیار فارسی مبتنی بر مستندات رسمی لیارا که در دو سطح صفحه کامل و Popup در
دسترس است. سیستم فقط وقتی پاسخ فنی می‌دهد که evidence کافی از corpus رسمی داشته
باشد؛ citationها از metadata سرور ساخته می‌شوند و مدل اجازه ساخت URL ندارد.

> وضعیت تحویل: **Release Candidate**. کد، تست‌ها و artifactهای استقرار آماده‌اند؛
> انتشار Production نهایی همچنان به حساب لیارا، Secretهای مستقل، ingestion و
> عبور smoke/eval همان محیط نیاز دارد.

## اجرای سریع برای داورها

راهنمای مرحله‌به‌مرحله و سناریوهای امتیازدهی در
[`docs/runbooks/judging.md`](./docs/runbooks/judging.md) قرار دارد. خلاصه مسیر:

```bash
mkdir liara-assistant-demo
cd liara-assistant-demo

git clone https://github.com/Mohuva13/Liara_ChatBot.git Liara
git clone https://github.com/liara-cloud/docs.git docs

cd Liara
cp .env.example .env
```

مقادیر واقعی را فقط در `.env` محلی ignored وارد کنید. حداقل این موارد لازم‌اند:

```dotenv
POSTGRES_PASSWORD=<local-strong-password>
DATABASE_URL=postgresql://liara_assistant:<local-strong-password>@postgres:5432/liara_assistant
API_INTERNAL_TOKEN=<random-token-at-least-32-bytes>

LLM_API_KEY=<provider-secret>
EMBEDDING_API_KEY=<provider-secret>
```

در اولین اجرا corpus رسمی باید ingest شود:

```bash
LIARA_RUN_INGESTION=1 ./scripts/start-local.sh
```

اگر Docker برای کاربر فعلی مجاز نیست:

```bash
sudo env LIARA_RUN_INGESTION=1 ./scripts/start-local.sh
```

پس از فعال‌شدن corpus، اجراهای بعدی embedding جدید مصرف نمی‌کنند:

```bash
./scripts/start-local.sh
```

- چت کامل: <http://localhost:3000/chat>
- Popup: <http://localhost:3000>
- Liveness: <http://localhost:8000/health/live>
- Readiness: <http://localhost:8000/health/ready>

توقف سرویس‌ها بدون حذف داده‌های PostgreSQL و Redis:

```bash
./scripts/stop-local.sh
```

## چرا این محصول قابل اعتماد است؟

- **Corpus رسمی:** فقط `liara-cloud/docs/public/llms/**/*.md` منبع پاسخ است.
- **Hybrid RAG:** lexical/trigram و exact vector مستقل اجرا، با RRF ادغام و سپس
  rerank می‌شوند.
- **Evidence gate:** relevance، پوشش entity، تناقض و بودجه evidence پیش از
  generation بررسی می‌شوند.
- **Citation امن:** source ID توسط مدل پیشنهاد می‌شود، ولی URL و کارت منبع فقط از
  metadata allowlistشده‌ی `docs.liara.ir` ساخته می‌شوند.
- **Fail-closed:** نبود شاهد به سؤال تکمیلی یا Support/Ticket می‌رسد، نه پاسخ
  حدسی. fallback استخراجی فقط برای گزاره منفی صریح با پوشش کامل entityها مجاز است.
- **Session سرورمحور:** browser مالک history نیست؛ context محدود و شمارنده issue
  در Redis با TTL نگهداری می‌شود.
- **کلید server-only:** هیچ provider key یا connection string به browser منتقل
  نمی‌شود.

## قابلیت‌های محصول

### کیفیت پاسخ و RAG

- ingestion incremental، idempotent، resumable و atomic با content hash، source
  commit، canonical URL، heading path و language metadata
- chunking آگاه از heading و code fence؛ command یا code block نصف نمی‌شود
- redaction credentialهای نمونه پیش از index و secret scan روی repository
- بازیابی follow-up با context محدود؛ پاسخ‌هایی مانند «پایتون» ادامه سؤال تکمیلی
  قبلی محسوب می‌شوند
- تشخیص entityهایی مانند Redis، PostgreSQL، Pgvector، HNSW و platformها برای
  جلوگیری از source نامرتبط
- generation ساختاریافته با JSON mode و اعتبارسنجی claim/source پیش از نمایش
- primary/backup provider، timeout، retry با jitter، circuit breaker و bulkhead

### UI و تجربه مکالمه

- Next.js App Router، TypeScript، AI SDK UI، AI Elements و shadcn/ui
- Page و Popup با session مشترک، RTL فارسی و محتوای فنی LTR-isolated
- تم روشن، تیره و هماهنگ با تنظیم سیستم
- Markdown امن، source card، code block، Copy و Download واقعی
- loading، ready، Stop، Retry، offline/error، no-answer و Support state
- Responsive از عرض 320 تا 1440 پیکسل، keyboard/focus و reduced-motion
- سطح پاسخ بدون selector دستی و بر اساس شواهد همان مکالمه تنظیم می‌شود

### امنیت، پایداری و هزینه

- distributed rate limit با Redis، idempotency و `Retry-After`
- same-origin adapter، origin validation، request-size limit، cookie امن و CSP
- log ساختاریافته بدون prompt، متن کامل کاربر، chunk یا PII
- Prometheus metrics و OTLP اختیاری برای latency، outcome، token، cache و provider
- مدل کوچک برای سؤال مستقیم و مدل بزرگ فقط برای مسیرهای پیچیده
- سقف context/evidence/output، response cache و usage/cost telemetry

## معماری

```text
Browser
  -> Next.js /api/chat (same-origin adapter)
  -> FastAPI /v1/chat/stream
       -> Redis: session, rate limit, idempotency, cache, failure counters
       -> PostgreSQL + Pgvector: corpus, lexical/trigram, exact vectors
       -> AvalAI/OpenAI-compatible provider: structured completion + embeddings
  <- validated text chunks + server-built sources/support/usage
```

FastAPI مالک scope، intent، retrieval، confidence، model routing، policy و provider
call است. Next.js منطق RAG را تکرار نمی‌کند. completion مدل عمداً non-stream است،
چون JSON و citationها باید پیش از نمایش کامل validate شوند؛ پس از validation،
backend متن را به شکل eventهای chunked برای UI می‌فرستد.

## ساختار repository

```text
backend/                 FastAPI، ingestion، RAG، provider و policy
frontend/                Next.js، Page/Popup و adapter هم‌مبدأ
backend/migrations/      PostgreSQL/Pgvector migrations
evals/datasets/          golden dataset نسخه‌بندی‌شده
docs/discovery/          audit corpus و سامانه قبلی
docs/reports/            گزارش پوشش معیارهای داوری
docs/runbooks/           اجرای داوری، توسعه محلی و استقرار Production
scripts/                 start/stop، secret scan و release eval
spec.md                  نیازمندی‌ها و acceptance criteria
VIBE_CODING_BRIEF.md     معماری و تصمیم‌های اجرایی
```

## تنظیم Environment

مرجع کامل و بدون Secret در [`.env.example`](./.env.example) است. گروه‌های اصلی:

| گروه | متغیرهای مهم |
|---|---|
| Backend | `APP_ENV`, `WEB_ORIGIN`, `API_INTERNAL_TOKEN` |
| Data | `DATABASE_URL`, `REDIS_URL`, `DOCS_REPO_PATH` |
| LLM | `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_SMALL_MODEL`, `LLM_LARGE_MODEL` |
| Backup | `LLM_BACKUP_BASE_URL`, `LLM_BACKUP_API_KEY` |
| Embedding | `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` |
| Policy | `SESSION_TTL_SECONDS`, `RATE_LIMIT_*`, `EVIDENCE_*`, `MAX_*_TOKENS` |
| Monitoring | `METRICS_BEARER_TOKEN`, `OTEL_EXPORTER_OTLP_ENDPOINT` |

`LLM_BACKUP_API_KEY` باید credential مستقل داشته باشد؛ تکرار primary key در backup
از اتمام quota یا لغو هم‌زمان جلوگیری نمی‌کند. فایل `.env` واقعی ignored است و
نباید commit شود.

## اجرای دستی بدون Compose

پیش‌نیازهای توسعه: Python 3.11، Node.js 22، pnpm 11، PostgreSQL دارای Pgvector و
Redis.

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
.venv/bin/uvicorn app.main:app --reload --port 8000

cd ../frontend
pnpm install --frozen-lockfile
API_INTERNAL_BASE_URL=http://localhost:8000 pnpm dev
```

در نبود PostgreSQL، Redis، corpus فعال یا provider، `/health/live` می‌تواند سالم
باشد ولی `/health/ready` عمداً `503` می‌دهد. جزئیات در
[`docs/runbooks/local-development.md`](./docs/runbooks/local-development.md) است.

## گیت‌های کیفیت

```bash
cd backend
.venv/bin/ruff format --check app tests
.venv/bin/ruff check app tests
.venv/bin/mypy app
.venv/bin/pytest -q

cd ../frontend
pnpm lint
pnpm exec tsc --noEmit
pnpm test -- --run
pnpm build

cd ..
bash scripts/secret-scan.sh
backend/.venv/bin/python scripts/verify-eval-dataset.py
```

آخرین baseline ثبت‌شده: 79 تست backend، 20 تست frontend، Mypy/Ruff/ESLint/TypeScript
سبز، build تولیدی موفق و secret scan پاک. نتیجه محیط واقعی باید دوباره توسط داور
اجرا و ثبت شود.

## معیارهای داوری 300 امتیازی

| معیار | سقف | محل شاهد |
|---|---:|---|
| کیفیت و صحت پاسخ‌ها | 80 | `backend/app/retrieval`, `backend/app/generation`, release eval |
| طراحی UI و تجربه کاربری | 55 | `frontend/src/features/chat`, Page/Popup smoke |
| Agentic و Personalization | 50 | session context، clarification و failure state machine |
| امنیت، پایداری و Monitoring | 50 | policyها، metrics، threat model و failure tests |
| استقرار روی لیارا | 40 | Dockerfile، `liara.json` و deployment runbook |
| بهینه‌سازی هزینه | 25 | routing، budgets، cache و usage telemetry |

شرح دقیق پیاده‌سازی و gateهای محیطی:

- [راهنمای اجرای داوری](./docs/runbooks/judging.md)
- [گزارش معیارهای داوری](./docs/reports/final-criteria-report.md)
- [وضعیت پذیرش](./docs/acceptance-status.md)
- [راهنمای Production روی لیارا](./docs/runbooks/deployment.md)
- [Threat model](./docs/threat-model.md)

## استقرار روی لیارا

توپولوژی Production شامل frontend عمومی و backend/PostgreSQL/Redis در یک شبکه
خصوصی است. Secretها فقط از Environment/Secret Manager لیارا وارد می‌شوند. مراحل
کامل ساخت منابع، env matrix، migration، ingestion، smoke، monitoring، backup و
rollback در [`docs/runbooks/deployment.md`](./docs/runbooks/deployment.md) آمده است.

## عیب‌یابی سریع

### Readiness برابر 503 است

```bash
docker compose ps
docker compose logs --tail=120 backend postgres redis
curl -i http://localhost:8000/health/ready
```

علت معمول: corpus هنوز active نشده، connection string اشتباه است یا provider
پیکربندی نشده است. در اولین اجرا ingestion را فعال کنید.

### UI می‌گوید پاسخ دریافت نشد

```bash
docker compose logs --since=5m backend frontend
```

UI پیام امن backend را نمایش می‌دهد و متن سؤال را برای Retry حفظ می‌کند. نام مدل،
quota، timeout و `API_INTERNAL_TOKEN` را بررسی کنید. مسیر generation از completion
غیرstream با `response_format=json_object` استفاده می‌کند.

### ingestion قطع شد

همان دستور را دوباره اجرا کنید؛ batchهای موفق checkpoint شده‌اند و فقط embeddingهای
ناقص ادامه پیدا می‌کنند:

```bash
LIARA_RUN_INGESTION=1 ./scripts/start-local.sh
```

### پاک‌سازی کامل محیط محلی

دستور زیر volumeهای محلی PostgreSQL و Redis و corpus ingestشده را حذف می‌کند و
قابل بازگشت نیست:

```bash
docker compose down --volumes --remove-orphans
```

## اسناد مرجع

1. [`spec.md`](./spec.md) — رفتار قابل‌آزمون و معیارهای پذیرش
2. [`VIBE_CODING_BRIEF.md`](./VIBE_CODING_BRIEF.md) — معماری و تصمیم‌ها
3. [`AGENTS.md`](./AGENTS.md) — قرارداد توسعه و Definition of Done
4. [`agent.md`](./agent.md) — What / Why / How محصول

## مجوز و مالکیت منابع

این repository کد دستیار را نگه می‌دارد. محتوای مستندات متعلق به repository رسمی
[`liara-cloud/docs`](https://github.com/liara-cloud/docs) است و هنگام ingestion به
صورت مستقل دریافت می‌شود.
