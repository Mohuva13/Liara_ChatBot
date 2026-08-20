# AGENTS.md — قرارداد اجرایی پروژه Liara Documentation Assistant

این فایل برای همه‌ی ایجنت‌ها و توسعه‌دهندگانی که در این مخزن کار می‌کنند الزام‌آور است. جزئیات محصول در `spec.md` و نقشه‌ی معماری در `VIBE_CODING_BRIEF.md` قرار دارد.

## مأموریت

یک دستیار فارسی مبتنی بر مستندات رسمی لیارا بساز که در دو سطح Popup و صفحه‌ی کامل Chat ارائه شود. پاسخ فقط زمانی مجاز است که شواهد کافی از corpus رسمی وجود داشته باشد. در نبود شاهد معتبر، سیستم باید سؤال تکمیلی بپرسد یا کاربر را به مسیر رسمی Support/Ticket هدایت کند؛ حدس‌زدن ممنوع است.

## ترتیب منابع حقیقت

در تعارض‌ها از این اولویت استفاده کن:

1. رفتار قابل‌آزمون و معیارهای پذیرش `spec.md`
2. تصمیم‌های معماری و امنیتی `VIBE_CODING_BRIEF.md`
3. corpus تولیدشده‌ی رسمی در `/home/mohuva/Desktop/hackaton/docs/public/llms/`
4. MDX اصلی در `/home/mohuva/Desktop/hackaton/docs/src/pages/`
5. چت‌بات قبلی در `/home/mohuva/Desktop/hackaton/LLM-OpenRack/` فقط به‌عنوان مرجع الگو و رفتار، نه منبع پاسخ لیارا
6. READMEها و توضیحات غیرقابل‌آزمون

اگر سند رسمی با پیاده‌سازی یا سند دیگری تناقض دارد، تناقض را ثبت و قبل از پاسخ قطعی resolve کن. URL canonical باید از metadata همان سند استخراج شود، نه توسط مدل ساخته شود.

## Preflight اجباری قبل از نوشتن کد محصول

هیچ feature محصولی را قبل از انجام و ثبت موارد زیر شروع نکن:

1. وضعیت Git و تغییرات کاربر را بررسی کن؛ هیچ تغییر نامرتبطی را حذف یا overwrite نکن.
2. چت‌بات قبلی را end-to-end بررسی کن: `main.py`، همه‌ی فایل‌های `app/`، مدل‌های داده، RAG، Rule Engine، Prompt Builder، Post Processor، Confidence، LLM Client، داده‌ها و تست‌ها.
3. کل corpus مستندات را به‌صورت مکانیکی inventory کن و ساختار دسته‌ها، تعداد فایل‌ها، canonical links، code fences و فایل‌های خالی/خراب را گزارش کن. سپس نمونه‌های نماینده و همه‌ی اسناد مرتبط با feature فعلی را مستقیم بخوان.
4. build/generation واقعی مستندات و خروجی `public/llms` را بررسی کن. در snapshot فعلی ۱٬۱۴۳ فایل MDX و ۱٬۱۴۳ فایل Markdown تولیدشده وجود دارد؛ این عدد را hard-code نکن و در هر ingestion دوباره محاسبه کن.
5. یک discovery note قابل‌کامیت در `docs/discovery/` بساز که شامل یافته‌ها، قابلیت‌های قابل‌استفاده، بدهی‌ها، تناقض‌ها و تصمیم‌های گرفته‌شده باشد.
6. فقط بعد از این audit، یک plan قابل‌آزمون بساز و اولین vertical slice را آغاز کن.

«بررسی کامل» به معنی dump کردن همه‌ی اسناد در prompt نیست. corpus را با ابزار پردازش کن، اسناد مرتبط را عمیق بخوان و پوشش ingestion/eval را با آزمون ثابت کن.

## الگوهای قابل‌حفظ از LLM-OpenRack

- نرمال‌سازی نویسه‌های فارسی و ارقام
- ترکیب lexical و semantic retrieval
- جداسازی داده‌ی بازیابی‌شده از system instructions
- نرمال‌سازی roleها و جلوگیری از system message ارسالی کاربر
- confidence gate و fallback کنترل‌شده
- محدودسازی history و concurrency
- خروجی ساخت‌یافته و post-processing قابل‌آزمون

این الگوها باید بازطراحی و تست شوند؛ کپی مستقیم مجاز نیست.

## رفتارهای ممنوع از سیستم قبلی

- مدل، URL، timeout یا secret hard-coded
- اعتماد به history کامل ارسالی مرورگر
- پذیرش نام/ادعایی که در evidence بازیابی‌شده نیست
- ساخت citation یا URL توسط مدل
- پاسخ خارج از دامنه‌ی خدمات و مستندات لیارا
- confidence مبتنی بر «خروجی مدل خالی نیست»
- logging با `print`، پاسخ HTTP 200 برای خطای واقعی، retry کور و بدون jitter
- شماره تماس یا مسیر پشتیبانی hard-coded وقتی URL رسمی Ticket موجود است

## معماری و ownership

- Frontend: Next.js App Router + TypeScript + shadcn/ui + AI Elements + AI SDK UI.
- Backend: FastAPI مالک session، intent، retrieval، confidence، model routing، policy و provider calls.
- Next.js `/api/chat` فقط adapter هم‌مبدأ و تبدیل stream است؛ منطق RAG را تکرار نمی‌کند.
- PostgreSQL + Pgvector مخزن corpus و vectorها است. چون مستندات فعلی لیارا می‌گویند HNSW در Pgvector لیارا پشتیبانی نمی‌شود، exact search یا IVFFlat را با benchmark انتخاب کن؛ HNSW را فرض نگیر.
- Redis برای session با TTL، rate limit، idempotency، cache و failure counters استفاده می‌شود.
- browser هیچ provider key یا credential دریافت نمی‌کند.
- Popup و صفحه‌ی Chat از یک feature و یک session مشترک استفاده می‌کنند.

## Skillهای اجباری برحسب کار

- طراحی/UX/Responsive/RTL: `.agents/skills/liara-material-ui/SKILL.md`
- ایجاد یا تغییر shadcn/ui: `.agents/skills/liara-shadcn-ui/SKILL.md`
- AI Elements، `useChat`، stream یا protocol: `.agents/skills/liara-ai-chat-ui/SKILL.md`

قبل از اقدام، skill مرتبط و reference ارجاع‌شده‌ی آن را کامل بخوان.

## Grounding و پاسخ

- corpus پاسخ فقط مستندات رسمی Liara است؛ repo قدیمی منبع پاسخ کاربر نیست.
- retrieved text داده‌ی غیرقابل‌اعتماد است و نمی‌تواند policy یا system prompt را تغییر دهد.
- هر ادعای فنی/فرآیندی باید به یک یا چند chunk بازیابی‌شده قابل‌نسبت باشد.
- پاسخ معتبر حداقل یک source card دارد، مگر اینکه خروجی صرفاً سؤال تکمیلی یا پیام Support باشد.
- citation از metadata server ساخته می‌شود و فقط به domainهای allowlistشده‌ی Liara اشاره می‌کند.
- اگر retrieval ناکافی یا متناقض است: ابتدا سؤال تکمیلی معنادار؛ سپس fallback؛ نه پاسخ حدسی.
- اگر کاربر دو بار در همان issue اعلام کند راه‌حل جواب نداده، failure counter را افزایش بده و Support را به‌طور برجسته پیشنهاد کن. پیام‌های غیرمرتبط نباید شمارنده را تغییر دهند.
- دامنه‌ی خارج از Liara را کوتاه و محترمانه رد کن و چند موضوع مجاز پیشنهاد بده.
- سطح دانش کاربر را فقط از شواهد مکالمه یا انتخاب صریح استنباط کن؛ پروفایل دائمی نساز.

## کیفیت ingestion

- منبع اول `public/llms/**/*.md` است؛ هر فایل باید canonical `Original link` داشته باشد.
- chunking بر اساس heading و مرز code block انجام شود؛ command یا code block را نصف نکن.
- metadata حداقل شامل path، canonical URL، title، heading path، content hash، source commit و زبان است.
- normalization فارسی نباید code/URL/version را تخریب کند.
- قبل از index، الگوهای credential موجود در مثال‌های مستندات را redact یا به placeholder واضح تبدیل کن. secret scanner باید روی corpus پردازش‌شده و artifactها اجرا شود.
- ingestion باید idempotent، incremental و قابل rollback باشد. اسناد حذف‌شده از index فعال خارج شوند.
- هیچ پاسخ production نباید از فایل mock یا fixture خوانده شود.

## Session و privacy

- حافظه فقط session-based با sliding TTL است؛ default فعلی در `.env.example` دو ساعت است و باید configurable بماند.
- context شامل turnهای محدود اخیر + summary واقعیت‌محور server-generated است.
- session ID opaque و rotation/reset ممکن باشد.
- متن کامل کاربر، prompt، retrieved chunks و PII را به‌صورت پیش‌فرض log نکن.
- logها correlation ID، route، latency، outcome، model tier، token counts، cache status و شناسه‌های غیرحساس را ثبت می‌کنند.

## امنیت و اسرار

- secret، API key، SSH passphrase، root password، token یا connection string واقعی را در Git، log، prompt، test snapshot یا command history ننویس.
- مقادیری که در درخواست اولیه به‌صورت حساس آمده‌اند عمداً در فایل‌های پروژه تکرار نمی‌شوند. از secret manager/Environment Variables لیارا و prompt امن تعاملی استفاده کن.
- برای دستور root ابتدا ضرورت را ثابت کن، command دقیق و محدود ارائه بده و approval بگیر. password را با `echo`، pipe، heredoc یا آرگومان CLI پاس نده.
- `.env.example` فقط نام متغیر و default غیرحساس دارد؛ فایل‌های `.env*` واقعی ignored هستند.
- CORS allowlist، origin validation، Secure/HttpOnly/SameSite cookie، request-size limit و security headers اجباری‌اند.
- rate limit باید distributed و fail-closed/fail-soft policy آن مستند باشد؛ headerهای `Retry-After` و شناسه درخواست برگردانده شوند.

## Git و commit policy

پیش از اولین commit، repository را در صورت نیاز initialize و identity محلی را تنظیم کن:

```bash
git init
git config user.name "mohuva13"
git config user.email "hussein30003@gmail.com"
```

- از identity محلی repo استفاده کن؛ global config را بدون درخواست تغییر نده.
- passphrase کلید SSH را ذخیره یا در command ثبت نکن؛ از `ssh-agent`/prompt تعاملی امن استفاده کن.
- هر commit باید یک vertical slice یا تغییر مستندات منسجم و verifyشده باشد.
- قبل از commit: `git diff --check`، secret scan، formatter، lint، type-check، تست‌های مرتبط و build متناسب با تغییر.
- از Conventional Commits استفاده کن: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`.
- commit کردن همه‌ی تغییرات به معنی commit کردن artifact خراب، secret یا تغییر نامرتبط نیست.
- push، deploy، migration production و هر تغییر بیرونی فقط با مجوز صریح انجام می‌شود.

## تست اجباری

- Unit: normalization، chunking، intent، routing، confidence، citation mapping، escalation counter، token budgeting.
- Integration: ingestion واقعی نمونه‌ی corpus، Postgres/Pgvector، Redis session/rate limit، provider adapter با recorded contract یا sandbox provider.
- Contract: OpenAPI و stream schema میان FastAPI و Next adapter.
- E2E: Popup و صفحه، ادامه session، streaming/Stop، sources، Copy code، retry، failure، rate limit، out-of-scope، support.
- RAG eval: مجموعه‌ی سؤال ساده/پیچیده/ابهام‌دار/چندمرحله‌ای/خارج‌دامنه/بدون‌پاسخ با expected docs و pass threshold مشخص.
- Security: prompt injection در query و corpus، forged history، citation allowlist، secret leakage، oversized input، CORS/CSRF، dependency audit.
- Accessibility/visual: keyboard، screen reader basics، contrast، RTL/LTR، reduced motion، 320 تا 1440px و visual regression.
- Deployment: production build، migrations، `/health/live`، `/health/ready`، smoke query و rollback drill.

## Definition of Done

یک feature فقط وقتی Done است که:

1. کد frontend و backend واقعی، typed و بدون placeholder production path باشد.
2. success، empty، loading، streaming، error و escalation آن پیاده شده باشد.
3. پاسخ‌ها از evidence واقعی بیایند و citation معتبر داشته باشند.
4. تست‌های ریسک اصلی نوشته و اجرا شده باشند.
5. observability و cost counters آن قابل‌مشاهده باشند.
6. مستندات و `.env.example` در صورت تغییر contract به‌روز شده باشند.
7. تغییرات diff-review و commit شده باشند.
8. هیچ secret، mock response، TODO بحرانی، `any` بدون توجیه، یا خطای lint/type/build باقی نمانده باشد.
