# Product & Engineering Specification

## Liara Documentation Assistant

| فیلد | مقدار |
|---|---|
| وضعیت | Implementation candidate — live release gates pending |
| زبان اصلی محصول | فارسی (`fa-IR`, RTL) |
| Frontend | Next.js App Router + TypeScript + shadcn/ui + AI Elements + AI SDK UI |
| Backend | FastAPI |
| منبع پاسخ | فقط مستندات رسمی Liara |
| حافظه | Session-based، محدود و دارای TTL |
| سطوح UI | Popup در سایت + صفحه‌ی کامل Chat |
| استقرار هدف | زیرساخت Liara |

## 1. هدف و مسئله

کاربر باید بتواند درباره‌ی محصولات، استقرار، تنظیمات، خطاها و فرآیندهای مستندشده‌ی لیارا سؤال بپرسد و پاسخ فارسی کاربردی، مستند و متناسب با سطح دانش خود بگیرد. پاسخ بدون evidence ممنوع است. وقتی corpus جواب قابل‌اعتماد ندارد، سیستم باید ابهام را رفع کند یا کاربر را به پشتیبانی رسمی هدایت کند.

## 2. اصول غیرقابل‌مذاکره

1. **Grounded only:** ادعای مدل بدون شاهد corpus رسمی به کاربر نمایش داده نمی‌شود.
2. **Citation by construction:** مدل URL تولید نمی‌کند؛ backend از metadata منبع، source card می‌سازد.
3. **No fake production path:** پاسخ، citation، metric، status، user یا integration ساختگی در runtime وجود ندارد.
4. **Server authority:** session، history، model routing، retrieval و policy در backend کنترل می‌شوند.
5. **Support is a valid outcome:** no-answer صادقانه بهتر از پاسخ حدسی است.
6. **One conversation, two surfaces:** Popup و صفحه‌ی Chat رفتار و session یکسان دارند.
7. **Secrets stay server-side:** هیچ credential در browser bundle یا repository قرار نمی‌گیرد.
8. **Quality before eloquence:** retrieval/evidence و صحت بر لحن و طول پاسخ اولویت دارند.

## 3. محدوده

### 3.1 در محدوده‌ی نسخه‌ی قابل‌ارائه

- ingestion incremental مستندات رسمی Liara
- Persian-aware hybrid search و reranking
- scope/intent detection و سؤال تکمیلی
- پاسخ grounded با citation و source cards
- session memory و follow-up
- سطح پاسخ beginner/intermediate/advanced در همان session
- فرآیندهای چندمرحله‌ای و next-step suggestions
- repeated-failure detection و Ticket escalation
- مدل API-based با small/large routing
- streaming، Stop، retry کنترل‌شده و خطاهای کامل
- Popup و full-page chat responsive
- Markdown، table، link و code rendering امن
- language label و Copy برای code blocks
- rate limiting، token budget، cache، logs، metrics و traces
- استقرار production-like روی Liara با Postgres/Pgvector و Redis
- unit/integration/contract/E2E/RAG/security/accessibility/deployment tests

### 3.2 خارج از محدوده‌ی اولیه

- پاسخ دانش عمومی خارج از خدمات Liara
- long-term memory یا پروفایل دائمی کاربر
- آموزش/fine-tune مدل روی داده‌ی کاربر
- اجرای خودکار command در زیرساخت یا حساب کاربر
- ایجاد/ویرایش Ticket بدون integration و مجوز صریح آینده
- تضمین قیمت/موجودی لحظه‌ای اگر سند رسمی آن را ثابت نمی‌کند
- نمایش chain-of-thought یا prompt داخلی

## 4. کاربران و سناریوها

### P1 — کاربر مبتدی

می‌خواهد یک پروژه را deploy کند، معنی اصطلاحات را نمی‌داند و به مراحل کوتاه با verification نیاز دارد.

### P2 — توسعه‌دهنده

خطا یا تنظیم فنی دارد و command/code، علت محتمل، نحوه‌ی بررسی و source دقیق می‌خواهد.

### P3 — DevOps/کاربر حرفه‌ای

مقایسه، محدودیت، شبکه، دیتابیس یا عیب‌یابی چندمرحله‌ای می‌خواهد و پاسخ فشرده‌تر با جزئیات فنی نیاز دارد.

### P4 — کاربر نیازمند Support

پاسخ در docs موجود نیست یا راه‌حل‌های مستند چند بار نتیجه نداده‌اند. باید با summary قابل‌کپی به مسیر رسمی Ticket هدایت شود.

## 5. جریان‌های حیاتی

### 5.1 سؤال مستقیم با شاهد قوی

1. دریافت پیام و session
2. scope/intent و normalization
3. retrieve/rerank
4. evidence کافی
5. انتخاب small model یا پاسخ deterministic
6. stream پاسخ
7. نمایش source card و next step
8. ثبت usage/outcome بدون متن حساس

### 5.2 سؤال مبهم

1. تشخیص ابهامی که answer path را تغییر می‌دهد
2. پرسیدن حداکثر یک سؤال تکمیلی متمرکز در هر turn
3. ذخیره‌ی state در session
4. ادامه‌ی retrieval با پاسخ کاربر

### 5.3 سؤال پیچیده/چندسندی

1. decomposition محدود به زیرسؤال‌های لازم
2. retrieval برای query اصلی و زیرqueryها با budget
3. deduplicate و rerank evidence
4. route به large model
5. پاسخ مرحله‌ای با verification points و citations

### 5.4 بدون پاسخ قابل‌اعتماد

1. evidence insufficiency یا contradiction
2. اگر clarification می‌تواند نتیجه را تغییر دهد، سؤال تکمیلی
3. در غیر این صورت عدم قطعیت شفاف
4. Support card با `https://console.liara.ir/tickets/create`
5. عدم generation پاسخ فنی حدسی

### 5.5 شکست تکراری

1. کاربر صریحاً می‌گوید راه‌حل برای همان issue جواب نداده است
2. failure count همان issue افزایش می‌یابد
3. بار اول: یک مسیر مستند جایگزین یا verification request
4. بار دوم: Support به primary action تبدیل می‌شود و summary قابل‌کپی ارائه می‌شود
5. موضوع جدید شمارنده‌ی issue قبلی را افزایش نمی‌دهد

### 5.6 خارج از دامنه

پاسخ کوتاه: این دستیار فقط درباره‌ی خدمات و مستندات لیارا پاسخ می‌دهد؛ سپس ۲–۳ starter مجاز پیشنهاد شود. provider call گران در موارد قطعی اجرا نشود.

## 6. نیازمندی‌های عملکردی

### ING — Ingestion و corpus

#### ING-001 — منبع رسمی

سیستم باید `public/llms/**/*.md` را از repository رسمی ingest کند. MDX اصلی برای trace/debug نگه داشته می‌شود، اما ورودی ترجیحی Markdown تولیدشده است.

**پذیرش:** تعداد فایل کشف‌شده، ingest‌شده، skipped، failed و deleted گزارش شود؛ هیچ فایل بدون canonical URL فعال نشود.

#### ING-002 — metadata

هر document/chunk باید حداقل این metadata را داشته باشد:

- stable ID
- source path
- canonical URL
- title
- heading path
- chunk ordinal
- content hash
- source commit SHA
- corpus version
- language
- code/language metadata در صورت وجود

**پذیرش:** از هر citation در پاسخ بتوان به file + heading + commit برگشت.

#### ING-003 — chunking ساختاری

chunking بر heading، paragraph، list، table و code fence آگاه است. command، code block، step list مرتبط و heading context نباید بی‌دلیل جدا شوند.

**پذیرش:** تست fixture واقعی ثابت کند code fence ناقص تولید نمی‌شود و heading path حفظ می‌شود.

#### ING-004 — نرمال‌سازی فارسی

ی/ک عربی، نیم‌فاصله، فاصله و ارقام برای search normalize شوند؛ نسخه‌ی نمایشی اصلی حفظ شود. code، path، URL، version و identifier normalize مخرب نشوند.

**پذیرش:** queryهای معادل با نویسه/رقم فارسی و عربی نتایج هم‌خانواده بدهند.

#### ING-005 — redaction

نمونه‌های credential-like در مستندات قبل از embedding و prompt context به placeholder امن تبدیل شوند، بدون حذف مفهوم آموزشی.

**پذیرش:** secret scanner روی processed corpus صفر finding تأییدنشده داشته باشد؛ مثال اتصال همچنان قابل‌فهم باشد.

#### ING-006 — incremental و idempotent

ingestion با hash/commit فقط اسناد تغییرکرده را upsert کند؛ اسناد حذف‌شده inactive شوند؛ اجرای مجدد همان commit state را تغییر ندهد.

**پذیرش:** دو اجرای متوالی روی corpus ثابت، zero content updates ثبت کند.

### RAG — Retrieval، grounding و پاسخ

#### RAG-001 — scope و intent

سیستم باید in-scope/out-of-scope و intentهای deployment، configuration، connection، troubleshooting، comparison، plan/cost، account/team و general-docs را تشخیص دهد.

**پذیرش:** macro F1 حداقل 0.90 روی eval versioned و out-of-scope recall حداقل 0.95.

#### RAG-002 — hybrid retrieval

semantic vector search و lexical/trigram search مستقل اجرا و با روش مستند مانند RRF ادغام شوند. Top-k و filter باید configurable باشند.

**پذیرش:** Recall@10 حداقل 0.90 و MRR@10 حداقل 0.75 روی golden queries؛ معیار نهایی بعد از baseline ثبت و regressions بیش از ۳ واحد درصد fail شوند.

#### RAG-003 — reranking

candidateهای محدود با reranker مناسب فارسی/چندزبانه مرتب شوند. reranker timeout fallback کنترل‌شده دارد.

**پذیرش:** nDCG@5 نسبت به retrieval بدون rerank بهبود معنادار یا حداقل عدم regression با هزینه/latency کمتر نشان دهد.

#### RAG-004 — evidence sufficiency

قبل از generation باید کف relevance، coverage و contradiction بررسی شود. confidence فقط ترکیب قابل‌کالیبره‌ی retrieval/coverage/citation/answer validation است، نه self-confidence مدل.

**پذیرش:** no-answer recall حداقل 0.95 و no-answer precision حداقل 0.90 روی مجموعه‌ی adversarial/unknown.

#### RAG-005 — grounded generation

مدل فقط از evidence با source ID پاسخ می‌دهد. داده‌ی corpus و user prompt نمی‌توانند system policy را تغییر دهند.

**پذیرش:** critical hallucination برابر صفر روی release eval؛ claim support rate حداقل 0.95.

#### RAG-006 — citations

هر پاسخ فنی موفق حداقل یک source دارد. source URL از allowlist و metadata است؛ card عنوان، URL و heading را نمایش می‌دهد.

**پذیرش:** citation URL validity برابر 100%، citation precision حداقل 0.95 و unsupported/generated URL برابر صفر.

#### RAG-007 — تناقض و freshness

اگر دو سند ناسازگارند، پاسخ قطعی داده نشود مگر precedence روشن باشد. corpus version و source commit در telemetry ثبت شوند.

**پذیرش:** سناریوی conflicting docs به clarification/support یا پاسخ دارای بیان تناقض و چند source منجر شود.

#### RAG-008 — ساختار پاسخ

پاسخ معمولاً شامل: نتیجه‌ی کوتاه، مراحل لازم، code/command در صورت نیاز، روش verification، sourceها و قدم بعدی است. طول بر اساس سؤال و سطح کاربر تنظیم می‌شود.

**پذیرش:** پاسخ ساده بدون زیاده‌گویی و پاسخ پیچیده بدون حذف مرحله‌ی حیاتی در human rubric امتیاز حداقل 4/5 بگیرند.

### CONV — Conversation، agentic و personalization

#### CONV-001 — session memory

history در Redis با TTL و حداکثر turn ذخیره شود. popup/page session مشترک داشته باشند. session reset پاک‌سازی واقعی انجام دهد.

**پذیرش:** follow-up وابسته به turn قبل موفق؛ session دوم هیچ داده‌ای از session اول دریافت نکند؛ بعد از expiry history قابل‌بازیابی نباشد.

#### CONV-002 — context budget

recent turns + summary server-generated استفاده شود. summary فقط facts/preferences صریح مرتبط با session را نگه دارد و ادعاهای دستیار را بدون evidence به حقیقت تبدیل نکند.

**پذیرش:** مکالمه‌ی طولانی سقف token را رد نکند و constraints اصلی کاربر بعد از summarization حفظ شوند.

#### CONV-003 — سؤال تکمیلی

فقط وقتی اطلاعات مفقود answer path را materially تغییر می‌دهد، یک سؤال کوتاه پرسیده شود. سؤال‌های قابل‌پاسخ مستقیم با پرسش غیرضروری متوقف نشوند.

**پذیرش:** clarification precision حداقل 0.85 و over-clarification rate زیر 10% در eval انسانی.

#### CONV-004 — سطح دانش

سیستم سطح `beginner/intermediate/advanced` را از انتخاب صریح یا شواهد همان session نگه می‌دارد. کاربر می‌تواند آن را تغییر دهد.

**پذیرش:** یک سؤال ثابت در سه سطح، جزئیات و توضیح متفاوت ولی facts/citations یکسان تولید کند.

#### CONV-005 — فرآیند چندمرحله‌ای

برای setup/troubleshooting، state مراحل و verification حفظ شود؛ کاربر بتواند بگوید در کدام مرحله است.

**پذیرش:** follow-up «این مرحله انجام شد» به تکرار کل راهنما منجر نشود و next incomplete step پیشنهاد شود.

#### CONV-006 — repeated failure و Support

failure count per issue نگه داشته شود. پس از دومین failure صریح، Ticket CTA primary شود.

**پذیرش:** E2E با دو failure و یک topic change behavior دقیق را ثابت کند.

#### CONV-007 — next-step suggestions

پیشنهادها از answer/evidence فعلی مشتق شوند و action واضح باشند؛ حداکثر سه پیشنهاد.

**پذیرش:** suggestion خارج‌دامنه، تکراری یا بدون پشتوانه نمایش داده نشود.

### UI — رابط و تجربه

#### UI-001 — initial state

هر سطح قبل از اولین پیام شامل معرفی scope، چند starter واقعی و توضیح کوتاه درباره‌ی منابع/Support است. Chat خالی ممنوع.

#### UI-002 — popup

launcher دارای accessible name است؛ Popup در desktop bounded و در compact نزدیک full-screen می‌شود؛ Escape، close، focus trap/management و focus return درست است؛ controls اصلی سایت پوشانده نمی‌شوند.

#### UI-003 — full page

صفحه‌ی کامل reading width مناسب، composer پایدار، scroll-to-bottom کنترل‌شده و جای کافی برای code/source دارد. در expanded layout supporting pane فقط در صورت محتوای واقعی مجاز است.

#### UI-004 — shared conversation

رفتن از Popup به صفحه و برعکس نباید پیام یا streaming state را از بین ببرد یا duplicate کند.

#### UI-005 — message rendering

Markdown امن، list، table، link و code رندر شوند. HTML خام یا script اجرا نشود. Linkهای خارجی semantics و امنیت مناسب داشته باشند.

#### UI-006 — code blocks

هر code block زبان قابل‌مشاهده و Copy قابل‌دسترسی دارد. حداقل Bash، Python، JavaScript/TypeScript، JSON، YAML و fallback `text` پشتیبانی شوند. block LTR و horizontally scrollable است.

**پذیرش:** Copy byte-for-byte محتوای code را بدون prompt marker یا label کپی کند.

#### UI-007 — Sources

sourceها در card/section جدا از متن پاسخ نمایش داده شوند. title و link معنادار؛ duplicateها حذف؛ heading در صورت وجود نمایش داده شود.

#### UI-008 — chat lifecycle

submitted، streaming، ready، stopped، retryable error، fatal error، offline، rate limited، no-answer و support states طراحی و پیاده شوند. Stop باید upstream را abort کند.

#### UI-009 — responsive و RTL

در 320، 375، 768، 1024 و 1440px overflow افقی صفحه، control خارج viewport یا composer غیرقابل‌استفاده نباشد. محتوای فنی LTR isolate شود.

#### UI-010 — accessibility

Keyboard-only flow، focus visible، semantic landmarks، labelها، polite live regions، contrast، 200% zoom، touch target و reduced motion پاس شوند.

**پذیرش:** axe روی صفحات حیاتی zero critical/serious violation و سناریوی keyboard دستی کامل.

### API — قرارداد backend/frontend

#### API-001 — versioned API

Public contracts زیر `/v1` و OpenAPI source of truth باشند. TypeScript client/types از OpenAPI generate یا با contract test همگام شوند.

#### API-002 — chat stream

`POST /v1/chat/stream` envelope versioned و eventهای typed برای start/status/text/sources/suggestions/support/usage/end/error داشته باشد.

#### API-003 — idempotency و abort

`message_id` duplicate generation را منع کند. disconnect/Stop تا provider propagate شود.

#### API-004 — status codes

Input نامعتبر 400/422، duplicate 409، limit 429، provider unavailable 503 و timeout 504 است. خطا با HTTP 200 یا stack trace عمومی برگردانده نشود.

#### API-005 — health

- `/health/live`: سلامت process، بدون dependency call سنگین
- `/health/ready`: Postgres، Redis، corpus فعال، migration و provider configuration

### SEC — امنیت، پایداری و monitoring

#### SEC-001 — secrets

API key، cookie secret و DSN فقط env/secret manager. startup در production با secret مفقود fail شود. repository و artifacts secret-scan شوند.

#### SEC-002 — rate limit

Redis-backed limits بر session + IP hash + route؛ burst و sustained quota؛ `Retry-After`؛ عدم retry خودکار 429.

**پذیرش:** تست همزمانی نشان دهد quota بین چند instance مشترک است.

#### SEC-003 — input/browser security

Input length، request size، content type، CORS allowlist، origin validation، Secure/HttpOnly/SameSite cookie، CSP/security headers و Markdown sanitization.

#### SEC-004 — prompt injection

System prompt و provider config از user/history/corpus جدا؛ role allowlist؛ source content untrusted؛ exfiltration tests.

**پذیرش:** injection eval نتواند prompt، secret، خارج‌دامنه یا source جعلی تولید کند.

#### SEC-005 — failure handling

Timeout، retry محدود با backoff/jitter، circuit breaker، bulkhead/concurrency limit و graceful degradation. retry budget per request حداکثر configured value.

#### SEC-006 — structured observability

Logs JSON با request/session hash، route، latency، outcome، corpus version، model tier، token counts، cache hit و error code. متن خام/prompt/PII پیش‌فرض log نشود.

#### SEC-007 — metrics/traces

حداقل metrics:

- request count/error/latency/TTFT/stream duration
- retrieval latency/empty/low-confidence/reranker timeout
- grounded answer/citation coverage/no-answer/support rate
- tokens/model tier/provider errors/cache hits
- rate limits/session counts/abort counts

OpenTelemetry instrumentation و exporter configurable باشد.

#### SEC-008 — alerts

Alert برای error spike، provider failure، readiness failure، no-answer regression، citation failure، cost anomaly و latency p95 تعریف شود.

### COST — مدل و کنترل هزینه

#### COST-001 — provider adapter

Provider و model names config هستند. interface باید streaming، usage و timeout را یکسان کند. local Ollama dependency حذف شود.

#### COST-002 — routing

- deterministic/no-model: out-of-scope قطعی، policy message، برخی clarificationها
- small: سؤال مستقیم، evidence قوی، یک/دو سند، context کوتاه
- large: چندسندی، چندمرحله‌ای، ambiguity/diagnosis بالا

**پذیرش:** routing eval حداقل 90% ساده‌ها را بدون large model پاسخ دهد، بدون افت کیفیت زیر release gate.

#### COST-003 — token budget

قبل از call budget محاسبه شود؛ chunk dedupe، dynamic top-k، bounded history/summary، max output و stop conditions اعمال شوند.

#### COST-004 — cache

Caching فقط با key شامل normalized intent/query، corpus version، policy version، locale و knowledge level. پاسخ session-specific یا failure-sensitive بی‌احتیاط cache نشود.

#### COST-005 — cost visibility

usage واقعی provider و cost estimate per request/model/corpus version ثبت شود؛ dashboard روزانه/هفتگی و budget alert وجود داشته باشد.

### DEP — استقرار Liara

#### DEP-001 — topology

Next.js app، FastAPI app، PostgreSQL با Pgvector و Redis در private network. endpoint عمومی FastAPI فقط در صورت نیاز و با policy روشن.

#### DEP-002 — database index

HNSW روی Liara فرض نشود. exact vector search و IVFFlat با dataset واقعی benchmark و انتخاب ثبت شود.

#### DEP-003 — configuration

همه‌ی envها validate شوند؛ `.env.example` به‌روز؛ secret واقعی خارج Git؛ staging و production جدا.

#### DEP-004 — migrations و corpus

Schema migration versioned و backward-compatible؛ corpus version atomically فعال شود؛ rollback به corpus قبلی ممکن باشد.

#### DEP-005 — health و zero-downtime

Liara health check به readiness مناسب متصل شود؛ استقرار جدید پیش از traffic smoke test شود.

#### DEP-006 — rollback

دستور/فرآیند rollback code، database compatibility و corpus version مستند و حداقل یک بار در staging تمرین شود.

## 7. مدل داده‌ی مفهومی

### Document

`id`, `source_path`, `canonical_url`, `title`, `source_commit`, `content_hash`, `corpus_version`, `active`, timestamps

### Chunk

`id`, `document_id`, `heading_path`, `ordinal`, `content_original`, `content_normalized`, `embedding`, `token_count`, `content_hash`, `metadata`

### CorpusVersion

`id`, `source_commit`, `ingestion_status`, counts, `activated_at`, `previous_version_id`

### Session (Redis)

`session_id`, `created_at`, `last_seen_at`, `knowledge_level`, recent turns, factual summary, active issue, failure count, token budget state

### Turn

`message_id`, role, sanitized content, intent, model tier, source IDs, outcome, timestamps. Persist only as long as session policy allows.

### RetrievalTrace

request ID، query hashes، candidate IDs/scores، reranked order، thresholds، corpus version؛ بدون ذخیره‌ی بی‌قاعده‌ی PII.

## 8. SLO و performance targets

این اعداد launch target هستند و باید با provider/زیرساخت واقعی baseline شوند:

- Availability API پس از launch: 99.5% ماهانه، به‌جز maintenance اعلام‌شده
- p95 scope + retrieval: حداکثر 800ms در corpus هدف
- p95 time-to-first-token: حداکثر 4s برای small path و 7s برای large path
- p95 پاسخ کامل سؤال مستقیم: حداکثر 15s
- provider timeout: configurable و محدود؛ UI قابلیت Stop دارد
- ingestion incremental سند تغییرکرده: بدون rebuild اجباری کل corpus
- هیچ request نباید بیش از token budget configured provider call کند

## 9. Evaluation و release gates

### 9.1 مجموعه‌ی ارزیابی

حداقل شامل:

- هر حوزه‌ی اصلی docs: PaaS، DBaaS، AI، IaaS، Object Storage، Email، DNS، CLI/API/Console و Team
- سؤال ساده، پیچیده، چندسندی، typo، ارقام/نویسه‌های مختلف فارسی
- follow-up و pronoun/reference
- ambiguous و missing detail
- no-answer و out-of-scope
- prompt injection و source injection
- conflicting/stale docs
- repeated failure و Support
- code-heavy responses

هر case: `id`, query/turns, expected intent, expected/forbidden docs, answerable flag, required facts, forbidden claims, expected outcome.

### 9.2 Gateهای کیفیت

- Critical hallucination: **0**
- Source URL validity/allowlist: **100%**
- Claim support rate: **>= 95%**
- Citation precision: **>= 95%**
- No-answer recall: **>= 95%**
- Out-of-scope recall: **>= 95%**
- Intent macro F1: **>= 90%**
- Session isolation: **100%**
- Secret leakage tests: **0 failure**
- E2E critical flows: **100% pass**
- Accessibility critical/serious automated issues: **0**
- Production build/migrations/health/smoke/rollback rehearsal: **pass**

Release با regression بالاتر از tolerance ثبت‌شده یا بدون eval report ممنوع است.

## 10. نگاشت معیارهای داوری 300 امتیازی

| معیار | امتیاز | Requirement/evidence اصلی |
|---|---:|---|
| کیفیت و صحت پاسخ | 80 | ING-*, RAG-*, golden eval، citation/claim/no-answer gates |
| UI و تجربه کاربری | 55 | UI-001..010، E2E، visual regression، accessibility report |
| Agentic و Personalization | 50 | CONV-001..007، intent/clarification/failure eval |
| امنیت، پایداری، Monitoring | 50 | API-*، SEC-*، load/security/failure tests، dashboards/alerts |
| استقرار Liara | 40 | DEP-001..006، staging smoke، health، rollback evidence |
| بهینه‌سازی هزینه | 25 | COST-001..005، routing eval، token/cache/cost dashboard |
| **مجموع** | **300** | release evidence bundle |

## 11. تست‌ها

### Unit

Normalization، parser/chunker، redaction، intent، issue failure counter، routing، token budgeting، cache key، citation mapping، confidence.

### Integration

Corpus واقعی کوچک و نماینده، Postgres/Pgvector، Redis TTL/rate limit، provider adapter contract، ingestion idempotency/rollback.

### Contract

OpenAPI، error schema، SSE/NDJSON events و Next AI SDK adapter mapping.

### E2E

Popup/page، shared session، streaming/Stop، retry، code Copy، source cards، responsive، no-answer، out-of-scope، repeated failure، 429/503/504.

### Security

Prompt injection، corpus injection، forged role/history، source URL spoof، secret exfiltration، XSS Markdown، CORS/origin، oversized input، dependency/secret scan.

### Load/failure

Concurrent streams، Redis/Postgres/provider latency/failure، circuit breaker، backpressure، retry storm prevention و instance restart.

## 12. تحویل هر milestone

هر milestone باید این artifactها را داشته باشد:

1. کد و migration واقعی
2. تست و commandهای اجراشده
3. eval delta و regressions
4. screenshot/E2E evidence برای UI
5. metrics/log trace نمونه‌ی redacted
6. docs/ADR و `.env.example` به‌روز
7. secret scan و dependency scan
8. commit منسجم با Conventional Commit

## 13. Definition of Done نهایی

- همه‌ی Requirementهای P0 پیاده و trace شده‌اند.
- هیچ runtime mock یا local-model dependency وجود ندارد.
- پاسخ فنی بدون citation معتبر ممکن نیست.
- Support/no-answer/out-of-scope behavior تست شده است.
- Popup و صفحه روی session واحد و viewportهای هدف کار می‌کنند.
- code language + Copy تست شده است.
- model routing/token/cache و cost telemetry فعال است.
- rate limit/secrets/errors/logging/monitoring production-ready است.
- deployment روی Liara، readiness، smoke و rollback واقعاً اجرا و مستند شده است.
- همه‌ی تغییرات verify و commit شده‌اند.
