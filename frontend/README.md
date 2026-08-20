# Liara Assistant Frontend

رابط Next.js دستیار مستندات لیارا با App Router، TypeScript، Tailwind CSS، shadcn/ui، AI Elements و AI SDK UI.

## اجرا

از ریشه‌ی پروژه فایل `.env` را بر اساس `.env.example` بسازید؛ `API_INTERNAL_BASE_URL` باید به FastAPI اشاره کند.

```bash
pnpm install --frozen-lockfile
pnpm dev
```

صفحه‌ی اصلی گفتگو در `/chat` است. مسیر `/api/chat` یک adapter هم‌مبدأ است: session را از FastAPI می‌گیرد، فقط آخرین پیام کاربر را forward می‌کند و stream سرور را بدون اجرای RAG یا provider call در Next.js برمی‌گرداند.

## بررسی

```bash
pnpm lint
pnpm exec tsc --noEmit
pnpm build
```

در محیط فعلی build با fallback رسمی Webpack اجرا می‌شود؛ علت در `docs/discovery/compatibility-matrix.md` ثبت شده است.
