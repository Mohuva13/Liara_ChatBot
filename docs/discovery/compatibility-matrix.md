# ماتریس سازگاری frontend/backend

Snapshot: 2026-08-21

این سند gate پیش از scaffold است. minimumها از مستندات رسمی فعلی ابزارها آمده‌اند؛ نسخه‌ی دقیق resolved بعد از scaffold از lockfile خوانده و همین جدول به‌روزرسانی می‌شود.

## محیط محلی و baseline انتخابی

| جزء | محیط/نیاز فعلی | تصمیم |
|---|---|---|
| Node.js | local `22.23.1`; AI Elements حداقل 18 | Node 22 برای development/CI baseline |
| pnpm | local `11.19.0` | تنها package manager frontend؛ یک `pnpm-lock.yaml` |
| Next.js | AI Elements حداقل 14 و App Router پیشنهادی | `16.3.1`; App Router + `src/` |
| React | AI Elements نیازمند 19 | `19.2.8` |
| Tailwind CSS | AI Elements نیازمند 4 | `4.3.3` |
| shadcn/ui | CLI فعلی `init --rtl` را پشتیبانی می‌کند | init یک‌بار، `rtl: true`، بدون `--force` |
| AI Elements | component source محلی روی shadcn | فقط `message`, `conversation`, `prompt-input`, `sources`, `suggestion` |
| AI SDK UI | API فعلی transport-based است | `ai 7.0.69` + `@ai-sdk/react 4.0.72`؛ transport صریح و render از `parts` |
| Python | local `3.14.6` و `3.11` در دسترس | target `>=3.11,<3.15`؛ test env فعلی Python 3.11 |
| FastAPI/Pydantic | current stable در lock backend | async API، OpenAPI source of truth، Pydantic v2 settings |
| PostgreSQL/Pgvector | Liara Pgvector؛ HNSW unsupported | exact baseline؛ IVFFlat فقط پس از benchmark |
| Redis | سرویس Liara و private network | session/rate/idempotency/cache، TTL configurable |

در این محیط sandbox، Turbopack هنگام production build برای یک worker داخلی امکان bind کردن port نداشت. اسکریپت build از fallback رسمی `next build --webpack` استفاده می‌کند و type-check مستقل TypeScript نیز قبل از build اجرا می‌شود؛ این تصمیم مربوط به ابزار build است و معماری runtime را تغییر نمی‌دهد.

## منابع compatibility

- [AI Elements setup](https://elements.ai-sdk.dev/docs/setup): Node 18+، React 19، Next 14+، Tailwind 4، AI SDK و shadcn/ui.
- [shadcn CLI](https://ui.shadcn.com/docs/cli): `init --rtl`، add انتخابی و migration RTL.
- [AI SDK transport](https://ai-sdk.dev/docs/ai-sdk-ui/transport): transport صریح و same-origin `/api/chat`.
- [AI SDK useChat](https://ai-sdk.dev/docs/reference/ai-sdk-ui/use-chat): API transport-based و message parts.
- corpus رسمی Liara در commit ثبت‌شده در audit برای محدودیت‌های deployment/Pgvector.

## مرز نسخه‌های قدیمی corpus

نمونه‌ی Liara در `public/llms/ai/ai-sdk-ui/chatbot.md` از API نسل قدیمی‌تر مانند `content`, `handleSubmit` و `toDataStreamResponse` استفاده می‌کند. در API فعلی، input state مستقل، `sendMessage`, typed `parts`, `DefaultChatTransport` و UI message stream مبنا هستند.

تصمیم: برای پاسخ به کاربران، corpus رسمی Liara منبع حقیقت است؛ برای dependency/API implementation، مستندات رسمی current package و lockfile پروژه منبع حقیقت‌اند. این تفاوت در contract tests پوشش داده می‌شود.

## gateهای scaffold

1. `create-next-app` واقعی با TypeScript/App Router/Tailwind/ESLint و `src/`.
2. بررسی package manifest و lockfile پیش از shadcn.
3. `shadcn init --rtl` فقط وقتی `components.json` وجود ندارد.
4. نصب انتخابی AI Elements و diff-review source/dependencyهای generated.
5. هیچ provider secret یا model call در browser/Next business logic.
6. lint، type-check، test و production build قبل از commit.
7. نسخه‌های resolved و دلیل هر deviation از minimumها در این سند ثبت شوند.
