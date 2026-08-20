# Liara Documentation Assistant

پایه‌ی اجرایی دستیار فارسی مستندات رسمی لیارا؛ شامل رابط Next.js و API سرورمحور FastAPI.

## از کجا شروع کنیم؟

1. [AGENTS.md](./AGENTS.md) — قواعد اجرایی و Definition of Done برای ایجنت‌ها
2. [agent.md](./agent.md) — پاسخ What / Why / How و مرزهای محصول
3. [spec.md](./spec.md) — مشخصات محصول، نیازمندی‌ها و معیارهای پذیرش
4. [VIBE_CODING_BRIEF.md](./VIBE_CODING_BRIEF.md) — نقشه‌ی جامع معماری، پیاده‌سازی، تست و استقرار
5. [skillهای پروژه](./.agents/skills) — قراردادهای Material 3، shadcn/ui و AI chat UI

Discovery اجباری دو مخزن مرجع انجام و در [`docs/discovery`](./docs/discovery) ثبت شده است:

- مستندات رسمی لیارا: `/home/mohuva/Desktop/hackaton/docs/`
- چت‌بات قبلی: `/home/mohuva/Desktop/hackaton/LLM-OpenRack/`

## وضعیت vertical slice فعلی

- رابط فارسی RTL صفحه‌ی `/chat` با AI SDK UI، AI Elements و shadcn/ui
- state مشترک chat در provider ریشه برای استفاده‌ی بعدی Popup و صفحه‌ی کامل
- adapter هم‌مبدأ `/api/chat` که فقط آخرین پیام کاربر را به API نسخه‌بندی‌شده می‌فرستد
- API FastAPI برای liveness/readiness، صدور/حذف session و قرارداد `/v1/chat/stream`
- readiness واقعی PostgreSQL، corpus فعال، Redis و تنظیمات provider
- رفتار fail-closed: تا پیش از اتصال ingestion/retrieval/model، هیچ پاسخ ساختگی تولید نمی‌شود

## اجرای محلی

پیش‌نیازها: Node.js 22، pnpm 11 و Python 3.11.

```bash
cp .env.example .env

cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
.venv/bin/uvicorn app.main:app --reload --port 8000

cd ../frontend
pnpm install --frozen-lockfile
pnpm dev
```

صفحه‌ی چت روی `http://localhost:3000/chat` و health API روی `http://localhost:8000/health/live` در دسترس است. برای ready شدن API باید PostgreSQL/corpus، Redis و تنظیمات provider واقعاً در دسترس باشند.

## گیت‌های کیفیت

```bash
cd backend
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
.venv/bin/mypy app tests
.venv/bin/pytest

cd ../frontend
pnpm lint
pnpm exec tsc --noEmit
pnpm build
```

رمز، API key، passphrase و اطلاعات دسترسی نباید در Git ذخیره شوند. فقط نام متغیرها در `.env.example` نگهداری می‌شود و مقدار واقعی در تنظیمات Secret/Environment لیارا قرار می‌گیرد.
