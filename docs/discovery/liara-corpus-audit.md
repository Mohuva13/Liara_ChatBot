# ممیزی corpus رسمی مستندات Liara

تاریخ snapshot: ۱۴۰۵/۰۵/۳۰ (2026-08-21)  
Repository: `/home/mohuva/Desktop/hackaton/docs`  
Branch: `master`  
Commit: `dbb7430b1abc5bf92ccca3538f45c54bdc632fa8`

## inventory مکانیکی

منبع ingestion ترجیحی `public/llms/**/*.md` و منبع trace، `src/pages/**/*.mdx` است. شمارش‌ها در runtime هر ingestion دوباره محاسبه می‌شوند و در کد hard-code نخواهند شد.

| سنجه | نتیجه snapshot |
|---|---:|
| MDX در `src/pages` | 1,143 |
| Markdown در `public/llms` | 1,143 |
| Markdown خالی | 0 |
| جفت path یک‌به‌یک MDX/Markdown | 1,143 |
| canonical `Original link` معتبر روی `docs.liara.ir` | 1,143 |
| canonical تکراری | 0 |
| فایل با encoding خارج UTF-8/ASCII | 0 |
| خط code fence با backtick | 7,454 |
| فایل فاقد H1 | 1 |
| فایل مشکوک به fence نامتوازن با parser مکانیکی | 4 |
| فایل دارای candidate الگوی credential-like با heuristic گسترده | 190 |
| خطوط `public/all-links-llms.txt` | 1,145 |

توزیع top-level:

| دسته | فایل |
|---|---:|
| `paas` | 425 |
| `one-click-apps` | 190 |
| `dbaas` | 167 |
| `ai` | 127 |
| `iaas` | 66 |
| `references` | 65 |
| `email-server` | 38 |
| `object-storage` | 34 |
| `mirrors` | 21 |
| `dns-management-system` | 8 |
| `overview` | 2 |

فرمان‌های پایه:

```bash
git -C /home/mohuva/Desktop/hackaton/docs rev-parse HEAD
find src/pages -type f -name '*.mdx' | wc -l
find public/llms -type f -name '*.md' | wc -l
find public/llms -type f -name '*.md' -empty | wc -l
rg -l '^Original link: https://docs\.liara\.ir/' public/llms -g '*.md' | wc -l
rg '^```' public/llms -g '*.md' | wc -l
```

بررسی عمیق path parity، canonical uniqueness، UTF-8، H1 و fence state با یک اسکریپت read-only روی همه‌ی ۱٬۱۴۳ فایل انجام شد؛ fixture همین منطق در vertical slice ingestion به test پایدار تبدیل می‌شود.

## ناهنجاری‌های قابل‌اقدام

1. `public/llms/ai/ai-sdk-errors/ai-api-call-error.md` H1 ندارد و به‌جای محتوای سند، residue دستور converter را شامل می‌شود؛ تا اصلاح source/generator نباید active شود.
2. چهار خروجی زیر با parser fence-aware هنوز یک fence باز دارند و باید در ingestion quarantine یا با parser AST تأیید شوند:
   - `public/llms/ai/foundations/tools.md`
   - `public/llms/one-click-apps/liara-compose/fields-tables.md`
   - `public/llms/paas/docker/how-tos/set-envs.md`
   - `public/llms/paas/laravel/how-tos/configure-livewire-trusted-proxy.md`
3. scriptهای `generate-llms` در `package.json` به `mdx-to-md-converter` ارجاع می‌دهند، اما این directory در checkout فعلی وجود ندارد. بنابراین خروجی فعلی قابل‌مصرف است ولی build generation در این snapshot reproducible نیست.
4. heuristic گسترده‌ی credential-like روی ۱۹۰ فایل match دارد. بسیاری placeholder یا نام env هستند، اما نمونه‌های credential-shaped نیز وجود دارند. valueها در این audit ثبت نشده‌اند؛ redactor + secret scanner باید پیش از embedding/prompt اجرا شود.
5. بعضی نمونه‌های AI SDK در corpus به نسل قدیمی SDK pin شده‌اند. این corpus منبع پاسخ درباره Liara است، نه منبع انتخاب dependency frontend این پروژه.

## تناقض مستندات Pgvector

- cookbook مربوط به RAG، HNSW یا IVFFlat را به‌صورت عمومی پیشنهاد و در نمونه HNSW ایجاد می‌کند.
- سند بالاتر در precedence، `public/llms/dbaas/postgresql/quick-setup.md` صریحاً می‌گوید Pgvector لیارا HNSW را پشتیبانی نمی‌کند.

تصمیم: HNSW در topology لیارا استفاده نمی‌شود. exact search baseline است؛ IVFFlat فقط پس از dataset واقعی، `ANALYZE` و benchmark recall/latency انتخاب می‌شود. تناقض در پاسخ کاربر نیز نباید پنهان شود.

## نمونه‌های مستقیم خوانده‌شده

- AI SDK UI chatbot و Next.js App Router
- RAG chatbot cookbook
- FastAPI deployment و Next.js getting started
- PostgreSQL Pgvector extensions و quick setup
- Redis quick setup و private-network guidance
- Ticket creation و overview پشتیبانی
- همه‌ی فایل‌های anomaly بالا

این sample عمداً stratified است؛ پوشش کامل ingestion با processing مکانیکی و eval ثابت می‌شود، نه با dump corpus در prompt.

## قرارداد ingestion حاصل از audit

- canonical فقط از خط metadata parse و با `https://docs.liara.ir/` allowlist شود.
- BOM حذف شود، ولی content اصلی برای display/audit حفظ گردد.
- فایل فاقد title، canonical، UTF-8 یا fence سالم active نشود و reason گزارش شود.
- chunk بر heading/list/table/code boundary آگاه باشد و هیچ code block را نصف نکند.
- `path`, `canonical_url`, `title`, `heading_path`, `ordinal`, `content_hash`, `source_commit`, `language`, `code_language` ذخیره شوند.
- normalization فقط روی search copy اعمال شود؛ code، URL، identifier و version تغییر نکنند.
- secret-like valueها به placeholder معنایی تبدیل و فقط count/hash در report ثبت شود.
- ingestion incremental، idempotent، versioned، atomic activation و rollbackable باشد.
- سند حذف‌شده inactive شود؛ production هرگز fixture/mock corpus را نخواند.

## نتیجه gate

corpus برای ساخت pipeline مناسب است، اما ingest کور کل directory مجاز نیست. پنج anomaly محتوایی/ساختاری و generation gap باید در validator منعکس شوند. canonical coverage و path parity کامل، پایه‌ی خوبی برای citation-by-construction فراهم می‌کند.
