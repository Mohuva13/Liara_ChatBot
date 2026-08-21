# اجرای محلی و smoke test

## حالت UI بدون provider

این حالت برای بررسی RTL، Popup/Page، loading و error state کافی است و هیچ کلیدی مصرف نمی‌کند.

```bash
cp .env.example .env

cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
.venv/bin/uvicorn app.main:app --reload --port 8000

cd ../frontend
pnpm install --frozen-lockfile
API_INTERNAL_BASE_URL=http://localhost:8000 pnpm dev
```

- UI: `http://localhost:3000/chat`
- liveness: `http://localhost:8000/health/live`
- readiness بدون PostgreSQL/Redis/corpus/provider عمداً `503` است.

## حالت کامل با Pgvector و Redis

1. `.env` را از `.env.example` بسازید.
2. `POSTGRES_PASSWORD`، `DATABASE_URL`، `LLM_API_KEY` و `EMBEDDING_API_KEY` را فقط در `.env` محلی ignored یا Secretهای لیارا تنظیم کنید.
3. `DATABASE_URL` داخل Compose باید hostname برابر `postgres` داشته باشد.
4. سرویس‌ها را اجرا کنید:

```bash
docker compose up --build -d postgres redis backend frontend
docker compose exec backend python -m app.ingestion.cli --activate
curl --fail http://localhost:8000/health/ready
```

اجرای ingestion همان commit و manifest، embedding یا update تکراری انجام نمی‌دهد. نسخه فقط وقتی فعال می‌شود که همهٔ chunkها vector معتبر داشته باشند.

### اسکریپت‌های مدیریت محلی

اسکریپت start، imageهای production را build می‌کند و فقط پس از موفق بودن
liveness، readiness و صفحهٔ Chat پیام آماده بودن می‌دهد:

```bash
./scripts/start-local.sh
./scripts/stop-local.sh
```

به‌صورت پیش‌فرض start هیچ embedding جدیدی مصرف نمی‌کند. فقط وقتی corpus رسمی
تغییر کرده است ingestion افزایشی را صریحاً فعال کنید:

```bash
LIARA_RUN_INGESTION=1 ./scripts/start-local.sh
```

برای افزایش مهلت انتظار، `LIARA_START_TIMEOUT_SECONDS` را تنظیم کنید. اسکریپت
stop کانتینرها و شبکه را حذف می‌کند، ولی volumeهای PostgreSQL و Redis را نگه
می‌دارد.

## تست provider امن

کلید را در command، history یا فایل tracked قرار ندهید. ابتدا کلید افشاشده را rotate کنید؛ سپس مقدار جدید را در Secret/Environment وارد کنید. smoke query باید source card با دامنهٔ `docs.liara.ir` داشته باشد؛ پاسخ فنی بدون source شکست محسوب می‌شود.
