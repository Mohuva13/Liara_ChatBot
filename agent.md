# Agent Brief — What / Why / How

این فایل تصویر مشترک محصول را برای ایجنت Vibe Coding تعریف می‌کند. قواعد عملیاتی الزام‌آور در `AGENTS.md`، نیازمندی‌های قابل‌آزمون در `spec.md` و طراحی تفصیلی در `VIBE_CODING_BRIEF.md` است.

## 1) محصول

### What — چه چیزی می‌سازیم؟

یک دستیار گفت‌وگویی فارسی برای سایت لیارا که فقط از مستندات رسمی لیارا پاسخ می‌دهد و در دو سطح ارائه می‌شود:

- Popup قابل‌استفاده در صفحات سایت اصلی
- صفحه‌ی کامل Chat برای مکالمه‌ی طولانی‌تر، خواندن کد و بررسی منابع

هر دو سطح باید یک session، یک history و یک رفتار مشترک داشته باشند. پاسخ شامل متن فنی، code block، لینک و source card مستقل است. سیستم سؤال تکمیلی می‌پرسد، سطح پاسخ را با دانش کاربر هماهنگ می‌کند، قدم بعدی پیشنهاد می‌دهد و هنگام نبودن پاسخ قابل‌اعتماد یا شکست تکراری، کاربر را به Ticket رسمی هدایت می‌کند.

### Why — چرا می‌سازیم؟

- دسترسی سریع‌تر به بیش از هزار صفحه مستندات رسمی
- کاهش زمان جست‌وجو و تعداد پاسخ‌های نادرست یا ساختگی
- کمک به کاربران مبتدی و حرفه‌ای بدون جایگزین‌کردن Support انسانی
- تبدیل پاسخ به مسیر عملی با command، source و next step
- کسب امتیاز بالا در شش محور داوری: صحت، UX، Agentic/Personalization، امنیت/پایداری، استقرار لیارا و هزینه

### How — چگونه می‌سازیم؟

- corpus رسمی از `/home/mohuva/Desktop/hackaton/docs/public/llms/` ingest می‌شود.
- FastAPI intent، session، hybrid retrieval، reranking، confidence، model routing و policy را اجرا می‌کند.
- PostgreSQL/Pgvector اسناد و embeddingها را نگه می‌دارد؛ Redis session/rate-limit/cache را نگه می‌دارد.
- Next.js App Router رابط را با shadcn/ui، AI Elements و AI SDK UI می‌سازد.
- مدل زبانی از API و پشت adapter provider-agnostic فراخوانی می‌شود؛ API key فقط server-side است.
- پاسخ نهایی از evidence کنترل می‌شود و citation از metadata ساخته می‌شود.

## 2) منابع دانش

### What

دو repository باید قبل از توسعه عمیق بررسی شوند:

1. `/home/mohuva/Desktop/hackaton/docs/` — منبع حقیقت پاسخ‌ها
2. `/home/mohuva/Desktop/hackaton/LLM-OpenRack/` — مرجع الگوهای چت‌بات قبلی

مخزن docs در snapshot بررسی‌شده ۱٬۱۴۳ MDX و همان تعداد Markdown آماده‌ی LLM دارد. هر Markdown با `Original link` شروع می‌شود و `all-links-llms.txt` فهرست canonical ارائه می‌دهد.

### Why

استفاده از Markdown تولیدشده، وابستگی به rendering و scraping HTML را حذف می‌کند و heading، link و code fence را بهتر حفظ می‌کند. چت‌بات قبلی نیز الگوهای ارزشمندی مثل Persian normalization، hybrid retrieval و confidence gate دارد، اما دانش آن درباره OpenRack است و نباید منبع پاسخ Liara باشد.

### How

- inventory کل corpus با ابزار و checksum
- parse عنوان، heading tree، canonical URL و code blocks
- redact نمونه‌credentialها پیش از embedding
- chunk بر اساس معنا و heading، بدون بریدن command/code
- upsert incremental بر اساس content hash و commit SHA
- eval پوشش و citation روی نمونه‌های واقعی هر دسته

## 3) Grounded RAG و صحت پاسخ

### What

پاسخ تنها زمانی نمایش داده می‌شود که سؤال in-scope باشد، retrieval شواهد کافی برگرداند و ادعاها به sourceهای معتبر متصل باشند.

### Why

بیشترین امتیاز داوری متعلق به کیفیت و صحت است. یک پاسخ روان ولی بدون شاهد برای این محصول شکست محسوب می‌شود.

### How

Pipeline پیشنهادی:

```text
Normalize -> Scope/Intent -> Query rewrite -> Hybrid retrieve
-> Rerank -> Evidence sufficiency -> Model route -> Grounded generation
-> Claim/citation validation -> Stream final -> Observe/evaluate
```

- lexical/trigram و vector search با Reciprocal Rank Fusion ترکیب می‌شوند.
- reranker فقط top candidates را ارزیابی می‌کند تا هزینه محدود شود.
- مدل prompt شامل source IDهای صریح و دستور عدم حدس است.
- URL را مدل تولید نمی‌کند؛ backend source ID را به metadata معتبر map می‌کند.
- اگر evidence ناکافی است، به‌ترتیب سؤال تکمیلی، پاسخ «اطمینان کافی ندارم» و Support اجرا می‌شود.

## 4) Conversation و session memory

### What

حافظه فقط تا زمانی که session فعال است conversation و context را نگه می‌دارد.

### Why

کاربر باید follow-up طبیعی بپرسد، اما محصول نباید پروفایل دائمی یا history بی‌حد و پرهزینه بسازد.

### How

- session ID opaque و server-issued
- Redis با sliding TTL configurable
- turnهای اخیر + summary واقعیت‌محور و bounded
- deduplication با message ID
- reset واقعی session
- popup و صفحه روی یک session مشترک
- عدم اعتماد به history دستکاری‌شده‌ی browser

## 5) Agentic behavior و personalization

### What

سیستم intent را تشخیص می‌دهد، ابهام مؤثر را با یک سؤال کوتاه رفع می‌کند، فرآیندهای چندمرحله‌ای را به checklist تبدیل می‌کند و قدم بعدی مرتبط پیشنهاد می‌دهد.

### Why

کاربر فقط «متن» نمی‌خواهد؛ می‌خواهد استقرار، اتصال دیتابیس یا رفع خطا را به نتیجه برساند. با این حال ابزار نباید عملیات destructive یا account action را بدون مجوز انجام دهد.

### How

- intent taxonomy: راه‌اندازی، استقرار، پیکربندی، اتصال، عیب‌یابی، مقایسه، هزینه/پلن، حساب/تیم، خارج‌دامنه
- skill level: انتخاب صریح یا استنباط سبک از همان session (`beginner`, `intermediate`, `advanced`)
- answer plan: نتیجه‌ی کوتاه، مراحل، code، verification، source، next step
- repeated-failure state per issue: پس از دو اعلام شکست، Support primary action شود
- tool/actionهای آینده فقط با allowlist، confirmation و audit trail؛ MVP می‌تواند صرفاً راهنما باشد، نه اجرای خودکار

## 6) UI/UX

### What

رابط فارسی RTL، responsive، accessible و مناسب محتوای فنی با initial state واقعی، streaming، source card، code Copy و error states کامل.

### Why

یک chat خالی اعتماد و discoverability را کم می‌کند. کاربران موبایل و کاربران فنی باید بتوانند command و منابع را بدون اصطکاک استفاده کنند.

### How

- Material Design 3 برای adaptive layout، hierarchy، state و motion
- Liara brand cues و semantic tokens
- shadcn/ui برای primitives قابل‌مالکیت
- AI Elements برای `Message`, `Conversation`, `PromptInput`, `Sources`, `Suggestion`
- AI SDK `useChat` با transport صریح به Next same-origin adapter و سپس FastAPI
- code blocks LTR با label و Copy برای Bash/Python/JavaScript/JSON/YAML و زبان‌های دیگر
- تست 320/375/768/1024/1440، keyboard، contrast، reduced motion و screen-reader basics

## 7) API و backend

### What

FastAPI backend با API versioned، streaming، health/readiness، ingestion و telemetry.

### Why

منطق trust، session، retrieval و provider باید در یک backend قابل‌آزمون و قابل‌مانیتور باشد، نه در browser یا چند مسیر تکراری.

### How

حداقل endpointها:

- `POST /v1/chat/stream`
- `POST /v1/sessions`
- `DELETE /v1/sessions/{id}`
- `GET /health/live`
- `GET /health/ready`
- ingestion/admin خارج از public surface و با authentication مناسب

خطاها status واقعی و error code پایدار دارند. retry فقط برای خطاهای موقت، محدود، با backoff/jitter و idempotency انجام می‌شود.

## 8) مدل و هزینه

### What

مدل API-based با حداقل دو tier: ساده/ارزان و پیشرفته/قوی. نام مدل‌ها configuration هستند، نه hard-code.

### Why

همه‌ی سؤال‌ها به مدل گران نیاز ندارند. routing درست هم latency و هزینه را کاهش می‌دهد و هم کیفیت سؤال‌های پیچیده را حفظ می‌کند.

### How

- retrieval-only/template برای برخی رد دامنه یا clarificationهای قطعی
- small model برای سؤال مستقیم با evidence قوی و context کم
- large model برای چندسندی، چندمرحله‌ای، ambiguity بالا یا عیب‌یابی پیچیده
- token budget قبل از call، history summary، top-k پویا، output cap
- semantic cache فقط برای پاسخ‌های grounded و وابسته به corpus version
- ثبت token/cost/latency per route و جلوگیری از retry غیرضروری

## 9) امنیت و privacy

### What

Rate limiting، secret management، prompt-injection defense، CORS/origin policy، logging امن و کنترل failure.

### Why

چت عمومی مستقیماً در معرض abuse، هزینه‌ی API، دست‌کاری prompt و leakage قرار دارد.

### How

- API key و connection string فقط در Secret/Environment لیارا
- هیچ secret یا passphrase در Git/Markdown/log/command argument
- distributed rate limit در Redis بر اساس session/IP hash و endpoint
- request size و input length limits
- retrieved docs به‌عنوان untrusted data
- allowlist source URL
- عدم log متن خام به‌صورت پیش‌فرض؛ redaction و correlation ID
- dependency/secret scan در CI

اطلاعات حساس ارائه‌شده در درخواست اولیه عمداً در این فایل ثبت نشده‌اند. استفاده از آن‌ها فقط از مسیر امن تعاملی یا secret manager مجاز است.

## 10) Monitoring و پایداری

### What

Metrics، structured logs، traces، dashboards و alertهای مرتبط با کیفیت، هزینه و availability.

### Why

HTTP 200 به‌تنهایی نشان نمی‌دهد پاسخ grounded، مفید یا کم‌هزینه بوده است.

### How

- latency p50/p95، error rate، stream abort، provider failures
- retrieval empty/low-confidence، citation coverage، fallback/support rate
- token input/output، model tier، cache hit، cost estimate
- rate-limit events و session counts بدون PII
- OpenTelemetry و exporter configurable؛ Sentry اختیاری
- readiness شامل Postgres، Redis، corpus version و provider configuration؛ liveness فقط process

## 11) استقرار لیارا

### What

Frontend و Backend production-ready روی لیارا، با PostgreSQL/Pgvector و Redis در private network، health check و rollback.

### Why

استقرار صرفاً build موفق نیست؛ migration، secret، networking، readiness و rollback باید اثبات شوند.

### How

- artifactهای reproducible و lockfile واحد هر app
- محیط staging قبل از production
- migrations قبل از traffic switch با backward compatibility
- health checks رسمی Liara
- smoke test شامل یک سؤال grounded، یک no-answer و session continuation
- rollback code و schema/corpus version مستند

## 12) Git و تحویل

### What

Repository قبل از توسعه initialize و همه‌ی تغییرات منسجم پس از verification commit می‌شوند.

### Why

Vibe coding بدون checkpoint قابل‌بررسی، ریسک regression و از دست‌دادن تصمیم‌ها را بالا می‌برد.

### How

- local Git identity: `mohuva13 <hussein30003@gmail.com>`
- Conventional Commits و commitهای کوچک/منسجم
- secret scan + lint + type-check + tests + build پیش از commit
- استفاده از `ssh-agent` یا prompt امن برای passphrase؛ عدم ذخیره credential
- گرفتن approval برای push، deploy، root command و mutation بیرونی

## 13) Definition of Success

محصول موفق است اگر:

- روی golden eval پاسخ صحیح و مستند بدهد و hallucination بحرانی صفر باشد.
- پاسخ بدون source معتبر تولید نکند.
- follow-up همان session را بفهمد و session دیگر را آلوده نکند.
- popup و صفحه در همه viewportهای هدف کامل باشند.
- code Copy، RTL/LTR و source cards درست کار کنند.
- failure و abuse هزینه را کنترل کنند و به UI قابل‌فهم تبدیل شوند.
- روی Liara با health/readiness، monitoring و rollback واقعی deploy شود.
- هیچ بخش production به mock، secret committed یا مدل local hard-coded وابسته نباشد.
