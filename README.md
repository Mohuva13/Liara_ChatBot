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

## وضعیت پیاده‌سازی

- Page و Popup فارسی RTL با یک `ChatProvider` و session مشترک، streaming/Stop/Retry، source card، suggestion و Support card
- adapter هم‌مبدأ `/api/chat` که فقط آخرین پیام user را می‌پذیرد و stream نسخه‌بندی‌شده FastAPI را به AI SDK UI تبدیل می‌کند
- session محدود با sliding TTL، reset واقعی، idempotency، distributed rate limit و failure counter همان issue در Redis
- ingestion واقعی `public/llms/**/*.md`: canonical metadata، redaction، chunking آگاه از code fence، embedding batch و فعال‌سازی atomic نسخه در Pgvector
- hybrid lexical/trigram + exact-vector retrieval، RRF/rerank، evidence gate و citation فقط از metadata دامنه `docs.liara.ir`
- adapter قابل‌تعویض OpenAI-compatible برای AvalAI با timeout، retry محدود همراه jitter و model routing
- liveness/readiness، request limit، CORS/origin validation، security headers و telemetry ساخت‌یافته بدون متن prompt/user
- Docker/Liara config، Compose محلی، runbook، threat model، secret scan و eval dataset versioned

وضعیت پذیرش دقیق در [`docs/acceptance-status.md`](./docs/acceptance-status.md) ثبت می‌شود. تست زنده provider، integration واقعی Pgvector/Redis، load/restore drill و release eval تا فراهم‌شدن زیرساخت و یک کلید rotateشده، gate باقی می‌مانند؛ runtime در نبود آن‌ها fail-closed است.

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

صفحه‌ی چت روی `http://localhost:3000/chat` و health API روی `http://localhost:8000/health/live` در دسترس است. برای ready شدن API باید PostgreSQL/corpus فعال، Redis و تنظیمات provider واقعاً در دسترس باشند. راهنمای کامل و Compose در [`docs/runbooks/local-development.md`](./docs/runbooks/local-development.md) آمده است.

## گیت‌های کیفیت

```bash
cd backend
.venv/bin/ruff check .
.venv/bin/ruff format --check app tests
.venv/bin/mypy app
.venv/bin/pytest -q

cd ../frontend
pnpm lint
pnpm exec tsc --noEmit
pnpm test
pnpm build

cd ..
./scripts/secret-scan.sh
backend/.venv/bin/python scripts/verify-eval-dataset.py
```

رمز، API key، passphrase و اطلاعات دسترسی نباید در Git ذخیره شوند. فقط نام متغیرها در `.env.example` نگهداری می‌شود و مقدار واقعی در تنظیمات Secret/Environment لیارا قرار می‌گیرد.
