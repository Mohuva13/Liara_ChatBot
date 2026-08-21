# راهنمای جامع Vibe Coding

## Liara Documentation Assistant

این سند نقشه‌ی شروع تا تحویل پروژه است. ایجنت اجراکننده باید پیش از هر کدنویسی، `AGENTS.md`، `agent.md`، `spec.md` و skill مرتبط با task را بخواند و discovery دو مخزن مرجع را کامل کند.

---

## 1) مأموریت نهایی

یک چت‌بات فارسی production-grade برای Liara بساز که:

- فقط بر اساس مستندات رسمی Liara پاسخ دهد؛
- پاسخ ساده و پیچیده را با source معتبر ارائه کند؛
- در نبود evidence حدس نزند؛
- session و follow-up را تا پایان session نگه دارد؛
- سطح دانش کاربر را در همان session رعایت کند؛
- در ابهام سؤال تکمیلی و پس از شکست تکراری مسیر Support پیشنهاد کند؛
- هم Popup سایت اصلی و هم صفحه‌ی کامل Chat داشته باشد؛
- با Next.js، shadcn/ui، AI Elements و AI SDK UI در frontend و FastAPI در backend ساخته شود؛
- مدل local قبلی را با provider API قابل‌تعویض جایگزین کند؛
- rate limit، token/cost control، monitoring، tests و Liara deployment واقعی داشته باشد.

اصل مرکزی: **هر پاسخ یک تصمیم مبتنی بر evidence است، نه خروجی آزاد یک مدل.**

---

## 2) Discovery اجباری؛ قبل از ساخت پروژه

### 2.1 مخزن چت‌بات قبلی

مسیر:

```text
/home/mohuva/Desktop/hackaton/LLM-OpenRack/
```

حداقل این فایل‌ها و جریان اجرا را مستقیم بررسی کن:

```text
main.py
app/models.py
app/rule_engine.py
app/rag.py
app/prompt_builder.py
app/llm_client.py
app/post_processor.py
app/confidence.py
data/hardware_db.json
data/knowledge_base.json
test_postprocessor_final.py
verify_patch.py
requirements.txt
README*.md
```

#### واقعیت‌های استخراج‌شده از snapshot فعلی

- FastAPI دارای `/recommend` و `/health` است.
- Rule Engine با keyword/regex، intent و constraint می‌سازد.
- Hybrid RAG از `all-MiniLM-L6-v2` و FAISS استفاده می‌کند و lexical Persian scoring هم دارد.
- یک query embedding برای hardware و knowledge reuse می‌شود.
- history roleها normalize و به هشت پیام آخر محدود می‌شوند.
- Prompt Builder retrieved data را با delimiter از system rules جدا می‌کند.
- Ollama و `gemma3:27b`، URL و timeout 300s hard-code شده‌اند.
- Confidence فعلی ترکیب 40% rule، 40% retrieval و 20% stability است و threshold در کد 0.45 است؛ بعضی READMEها عدد دیگری گفته‌اند.
- stability عملاً فقط خالی‌نبودن متن مدل است و معیار groundedness نیست.
- Post Processor اجازه می‌دهد GPU/CPU نام‌برده‌شده توسط مدل حتی خارج RAG پذیرفته شود؛ این رفتار با هدف جدید تعارض دارد.
- history از client می‌آید و backend session store واقعی ندارد.
- citation، rate limit، structured telemetry و مدل routing وجود ندارد.
- تست عمدتاً به Post Processor و static validation محدود است.

#### چیزی که باید حفظ شود

- normalization فارسی
- hybrid lexical/semantic retrieval
- reusable query embedding
- structured data models
- role normalization و prompt-injection boundaries
- confidence/fallback concept
- concurrency limits و retry concept

#### چیزی که باید بازطراحی یا حذف شود

- Ollama/local model و hard-coded configuration
- client-authoritative history
- confidence غیرکالیبره
- پذیرش claim خارج evidence
- HTTP 200 برای error، `print` logging و retry کور
- OpenRack knowledge/hardware به‌عنوان منبع پاسخ

### 2.2 مخزن مستندات رسمی Liara

مسیر:

```text
/home/mohuva/Desktop/hackaton/docs/
```

#### واقعیت‌های استخراج‌شده از snapshot فعلی

- repository رسمی `liara-cloud/docs` است.
- ۱٬۱۴۳ صفحه‌ی MDX در `src/pages` دارد.
- ۱٬۱۴۳ Markdown تولیدشده در `public/llms` دارد؛ فایل خالی مشاهده نشد.
- همه‌ی فایل‌های بررسی‌شده با `Original link: https://docs.liara.ir/...` شروع می‌شوند.
- `public/all-links-llms.txt` فهرست لینک‌ها را ارائه می‌دهد.
- حوزه‌ها شامل PaaS، One-click Apps، DBaaS، AI، IaaS، References، Email، Object Storage، Mirrors و DNS است.
- corpus بیش از هفت هزار code fence دارد.
- بعضی مثال‌های مستندات مقدارهای credential-like دارند؛ پردازش امن/redaction پیش از embedding ضروری است.
- مستندات PostgreSQL لیارا Pgvector را پشتیبانی می‌کند، ولی صریحاً می‌گوید HNSW پشتیبانی نمی‌شود.
- مسیر رسمی Ticket در README و docs: `https://console.liara.ir/tickets/create`.
- مستندات AI لیارا سرویس OpenAI-compatible با `baseURL` و API key را شرح می‌دهد؛ version pinهای قدیمی AI SDK را بدون بررسی current docs کپی نکن.

#### روش بررسی «کامل»

1. `rg --files` و scriptهای deterministic برای inventory کل corpus.
2. counts و integrity: canonical link، title، heading، code fence balance، encoding و duplicate URL.
3. خواندن مستقیم همه‌ی فایل‌های مرتبط با feature در حال توسعه.
4. sample stratified از همه‌ی حوزه‌ها برای parser/chunker tests.
5. golden eval که پوشش کل taxonomy را اثبات کند.

خواندن ۱٬۱۴۳ فایل در یک prompt نه لازم است نه درست؛ coverage باید با pipeline و eval ثابت شود.

### 2.3 خروجی Discovery

پیش از scaffold کد، این artifactها را بساز و commit کن:

```text
docs/discovery/legacy-chatbot-audit.md
docs/discovery/liara-corpus-audit.md
docs/discovery/compatibility-matrix.md
docs/adr/0001-system-boundaries.md
```

هر audit باید command، commit SHA، counts، یافته، risk و تصمیم را داشته باشد.

---

## 3) Git و امنیت محیط توسعه

### 3.1 راه‌اندازی Git قبل از کدنویسی

اگر repository هنوز initialize نشده است:

```bash
cd /home/mohuva/Desktop/hackaton/Liara
git init
git config user.name "mohuva13"
git config user.email "hussein30003@gmail.com"
```

Identity را local تنظیم کن؛ global config را تغییر نده. از Conventional Commits و commitهای کوچک، منسجم و verifyشده استفاده کن.

### 3.2 passphrase، root و secrets

در درخواست اولیه اطلاعات حساس مطرح شده بود. آن مقادیر عمداً در این repository تکرار نشده‌اند و نباید وارد Markdown، `.env`, Git history، shell arguments، logs یا test snapshots شوند.

- SSH passphrase: فقط `ssh-agent` یا prompt تعاملی امن.
- root command: فقط در صورت ضرورت، با command محدود و approval؛ password را با pipe/echo/argument پاس نده.
- API key/DSN/cookie secret: Liara Environment/Secret settings.
- `.env.example`: فقط نام متغیر و default غیرحساس.
- قبل از هر commit secret scan اجرا شود.

### 3.3 چرخه‌ی هر تغییر

```text
Inspect -> Plan -> Implement vertical slice -> Test -> Review diff
-> Secret scan -> Commit -> Continue
```

push، deploy، production migration و تغییر بیرونی نیازمند مجوز صریح است.

---

## 4) ساختار پیشنهادی repository

دو app deployable مجزا در یک repository نگه دار تا مرز frontend/backend روشن و استقرار Liara قابل‌کنترل باشد:

```text
Liara/
├── AGENTS.md
├── agent.md
├── spec.md
├── VIBE_CODING_BRIEF.md
├── .agents/skills/
├── .env.example
├── frontend/
│   ├── src/app/
│   │   ├── (chat)/chat/page.tsx
│   │   ├── api/chat/route.ts
│   │   └── layout.tsx
│   ├── src/components/ui/              # shadcn-owned source
│   ├── src/components/ai-elements/     # AI Elements-owned source
│   ├── src/features/chat/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── transport/
│   │   ├── types/
│   │   └── tests/
│   ├── src/lib/
│   ├── components.json
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── liara.json
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── sessions/
│   │   ├── ingestion/
│   │   ├── retrieval/
│   │   ├── generation/
│   │   ├── policies/
│   │   ├── providers/
│   │   ├── observability/
│   │   └── models/
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   ├── Dockerfile or Liara Python config
│   └── liara.json
├── evals/
│   ├── datasets/
│   ├── graders/
│   ├── reports/
│   └── README.md
├── docs/
│   ├── discovery/
│   ├── adr/
│   ├── runbooks/
│   └── threat-model.md
├── scripts/
│   ├── verify-corpus.*
│   ├── run-evals.*
│   └── secret-scan.*
└── infra/
    └── liara/
```

اگر scaffold یا قابلیت واقعی مسیر دیگری می‌طلبد، با ADR تغییر بده؛ منطق RAG نباید بین frontend و backend پخش شود.

---

## 5) معماری مبنا

```text
                           Official docs repository
                         public/llms/**/*.md + commit
                                      │
                                      ▼
                            Ingestion / validation
                      parse -> redact -> chunk -> embed
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                 PostgreSQL + Pgvector       Corpus reports
                 docs/chunks/versions        hashes/errors

User ──> Popup or Chat page ──> Next.js /api/chat adapter
                                      │ private/authenticated hop
                                      ▼
                                FastAPI backend
        ┌──────────────┬──────────────┼───────────────┬──────────────┐
        ▼              ▼              ▼               ▼              ▼
   Session/Redis   Scope+Intent   Hybrid RAG      Policy/Confidence  Telemetry
        │                             │               │
        └──────────── context/evidence┴───────────────┘
                                      │
                               Model router
                         deterministic / small / large
                                      │
                           Liara AI or compatible API
                                      │
                     claim/source validation + stream
                                      │
                            text + source cards + next step
```

### 5.1 مرز مسئولیت‌ها

| جزء | مالکیت |
|---|---|
| Browser | input، interaction state، render، Stop، Copy، navigation |
| Next adapter | same-origin cookie/origin، schema adaptation، stream mapping |
| FastAPI | session truth، RAG، model، confidence، escalation، rate/cost policy |
| PostgreSQL | corpus، chunk، vector، version، ingestion metadata |
| Redis | session TTL، idempotency، distributed rate limit، cache، failure state |
| Provider API | generation/embedding پشت adapter؛ بدون دسترسی مستقیم browser |

### 5.2 چرا Next adapter؟

AI SDK UI به transport و UI message stream نیاز دارد. FastAPI نیز backend اجباری پروژه است. یک route کم‌حجم در Next:

- cookie و origin را هم‌مبدأ نگه می‌دارد؛
- eventهای FastAPI را به protocol موردانتظار `useChat` تبدیل می‌کند؛
- provider key را مخفی نگه می‌دارد؛
- بدون تکرار RAG یا policy، integration را پایدار می‌کند.

---

## 6) آماده‌سازی Frontend

### 6.1 Version compatibility gate

در زمان بررسی این سند، راهنمای current AI Elements نیازمندی‌هایی مانند React 19، Next.js 14+ App Router و Tailwind CSS 4 را اعلام می‌کند. این اعداد ممکن است تغییر کنند. قبل از scaffold، current official docs را بررسی و compatibility matrix را ثبت کن.

از pinهای قدیمی موجود در docs نمونه‌ی Liara (مثلاً AI SDK نسل قدیمی) صرفاً به‌دلیل وجود در corpus استفاده نکن. source code فعلی و docs رسمی packageها مرجع version انتخاب‌اند.

### 6.2 Scaffold برنامه

پس از discovery و Git baseline، یک Next.js واقعی با TypeScript، App Router، Tailwind و `src/` بساز. command دقیق را با current CLI verify کن؛ شکل مورد انتظار:

```bash
pnpm create next-app@latest frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/*"
```

### 6.3 shadcn/ui

از داخل `frontend/` و با package manager واحد:

```bash
pnpm dlx shadcn@latest init --rtl
```

اگر `components.json` وجود دارد، re-init نکن. `rtl: true`، aliasها و direction provider را verify کن.

### 6.4 AI Elements

حداقل موردنیاز:

```bash
npx ai-elements@latest add message
npx ai-elements@latest add conversation
npx ai-elements@latest add prompt-input
npx ai-elements@latest add sources
npx ai-elements@latest add suggestion
```

بعد از هر command، dependency و generated source را diff-review کن. `MessageResponse` باید code block syntax highlighting و Copy را واقعاً پشتیبانی و تست کند. component reasoning برای نمایش chain-of-thought استفاده نشود.

### 6.5 Component architecture

```text
ChatProvider / session transport
├── ChatLauncher
├── ChatPopup
│   └── ChatShell(surface="popup")
└── ChatPage
    └── ChatShell(surface="page")
        ├── ChatHeader
        ├── WelcomeState + Suggestions
        ├── Conversation
        │   └── ChatMessage
        │       ├── MessageResponse
        │       ├── Code blocks + Copy + language
        │       ├── Sources / SourceCard
        │       └── MessageActions
        ├── SupportCard
        ├── ChatStatus/ErrorState
        └── PromptInput + Submit/Stop
```

`ChatShell` تنها منبع rendering behavior باشد. Popup و Page wrapperهای layout هستند، نه دو implementation.

### 6.6 Material 3 + Liara style

- Material برای hierarchy، adaptive layout، state، elevation و motion.
- Liara blue و neutral docs surfaces برای identity.
- semantic CSS tokens، light/dark و CSS logical properties.
- compact/medium/expanded به جای device-specific CSS.
- initial state با value proposition و starterهای واقعی؛ هر starter یک سؤال واقعی به backend می‌فرستد.
- source card مستقل از answer.
- code/URL/ID LTR isolated در صفحه‌ی RTL.
- focus management، reduced motion و accessibility از ابتدا.

---

## 7) طراحی Backend FastAPI

### 7.1 ماژول‌ها

```text
core/config.py              validated settings; no hard-coded secrets
core/errors.py              stable internal/public error mapping
api/v1/chat.py              streaming endpoint
api/v1/sessions.py          create/reset
api/health.py               live/ready
sessions/store.py           Redis bounded state
sessions/context.py         recent turns + factual summary
ingestion/parser.py         Markdown/front matter/canonical URL
ingestion/redactor.py       example credential sanitization
ingestion/chunker.py        heading/code-aware chunks
ingestion/pipeline.py       incremental corpus versions
retrieval/normalizer.py     Persian normalization
retrieval/lexical.py        lexical/trigram ranking
retrieval/vector.py         Pgvector ranking
retrieval/fusion.py         RRF/dedup
retrieval/reranker.py       top-N rerank
retrieval/evidence.py       sufficiency/contradiction
generation/router.py        deterministic/small/large
generation/prompt.py        grounded source-ID prompt
generation/validator.py     claims/citations/output schema
providers/base.py           provider interface
providers/openai_compat.py  Liara AI/OpenAI-compatible API
policies/scope.py           in/out-of-scope
policies/escalation.py      clarification/repeated failure/support
policies/rate_limit.py      Redis distributed quotas
observability/*             logs/metrics/traces/cost
```

### 7.2 Provider interface

Provider باید حداقل این قابلیت‌ها را یکسان کند:

- `stream(messages, model, max_output_tokens, timeout, request_id)`
- usage واقعی input/output/cached tokens
- finish reason و abort
- typed provider errors
- embedding batch API

default deployment می‌تواند سرویس AI لیارا با OpenAI-compatible `baseURL` باشد؛ مدل و provider از env می‌آیند. backend باید با adapter تست شود تا تعویض provider، RAG/UI را تغییر ندهد.

### 7.3 API key migration از local به API

در سیستم قبلی `Ollama /v1/chat/completions` hard-code بود. مهاجرت صحیح:

1. حذف singleton دارای config ثابت.
2. Settings validation از env.
3. interface provider و adapter OpenAI-compatible async.
4. streaming واقعی و abort.
5. timeout/retry/circuit breaker.
6. usage telemetry و token caps.
7. مدل aliases `small` و `large` در config، نه model ID در business logic.
8. integration test با endpoint sandbox/recorded contract؛ production path بدون fake response.

---

## 8) Ingestion تفصیلی

### 8.1 ورودی

منبع ترجیحی:

```text
/home/mohuva/Desktop/hackaton/docs/public/llms/**/*.md
```

هر فایل باید:

- UTF-8 قابل‌خواندن باشد؛
- canonical `Original link` معتبر داشته باشد؛
- title قابل‌استخراج داشته باشد؛
- به domain مجاز `docs.liara.ir` اشاره کند.

### 8.2 parse و clean

1. BOM را مدیریت کن، نه اینکه content را خراب کنی.
2. Original link را metadata کن.
3. heading tree، paragraph، list، table، blockquote، code fence و link را parse کن.
4. footer تکراری `all links` را از embedding content حذف کن ولی source را تغییر نده.
5. navigation noise و media-only section را با rule قابل‌آزمون مدیریت کن.
6. relative links را با canonical page resolve و allowlist کن.

### 8.3 secret/example redaction

Corpus عمومی نمونه‌هایی شبیه password/token دارد. حتی اگر demo باشند، مدل نباید آن‌ها را به‌عنوان credential پیشنهادی تکرار کند.

Ruleها:

- key names مانند `*_PASSWORD`, `*_PASS`, `*_TOKEN`, `*_SECRET`, `*_API_KEY` را تشخیص بده.
- value را به `<YOUR_...>` تبدیل کن.
- ساختار code و نام env را حفظ کن.
- hash/redaction report ثبت کن؛ مقدار اصلی را در log نریز.
- false positiveهای version/hash با fixture کنترل شوند.

### 8.4 chunking

Target اولیه باید با tokenizer مدل embedding/generation سنجیده شود، نه تعداد character ثابت. پیشنهاد baseline:

- chunk حدود 350–700 token
- overlap معنایی 50–100 token فقط بین متن‌های پیوسته
- heading path در هر chunk
- code block و stepهای مرتبط یک atomic unit
- table بزرگ با header در هر split تکرار شود
- chunk خیلی کوتاه با sibling مرتبط merge شود

اعداد با retrieval eval tune شوند.

### 8.5 versioning و activation

```text
discovered -> parsed -> validated -> embedded -> indexed -> evaluated -> active
```

Version جدید فقط وقتی active شود که:

- parse failure زیر threshold و همه‌ی failures گزارش شده باشند؛
- canonical integrity پاس شود؛
- secret scan پاس شود؛
- smoke retrieval و eval حداقل پاس شوند.

activation atomic و rollback به version قبلی ممکن باشد.

---

## 9) Retrieval و confidence تفصیلی

### 9.1 Query preparation

- Unicode/Persian normalization برای search copy
- حفظ raw query برای display/audit hash
- resolve follow-up با session facts
- استخراج product/platform/error code/version بدون حذف token فنی
- query rewrite فقط با budget و trace؛ rewrite نباید intent جدید بسازد

### 9.2 Hybrid retrieval

دو ranking مستقل:

1. Vector cosine distance در Pgvector
2. Lexical/trigram یا search مناسب Persian برای exact command/error/product names

ترکیب baseline با Reciprocal Rank Fusion:

```text
RRF(document) = Σ 1 / (k + rank_i(document))
```

`k` و top-N با eval tune شوند. filter بر active corpus version و metadata معتبر اجباری است.

### 9.3 Pgvector روی Liara

مستندات فعلی Liara می‌گوید HNSW پشتیبانی نمی‌شود. بنابراین:

- برای corpus کوچک/متوسط exact search baseline بگیر.
- IVFFlat را فقط پس از کافی‌بودن داده، `ANALYZE` و benchmark واقعی فعال کن.
- recall/latency/memory/cost را ثبت کن.
- index choice را در ADR بنویس.

### 9.4 Reranking

- top 20–40 fused candidate ورودی reranker؛ top 4–8 evidence خروجی.
- heading/title/path در reranking لحاظ شود.
- duplicate یا near-duplicate chunk از یک section dedupe شود.
- timeout reranker به ranking fused fallback کند و metric ثبت شود.

### 9.5 Evidence sufficiency

Decision فقط یک threshold embedding نیست. حداقل این سیگنال‌ها:

- top relevance و margin
- lexical exactness برای command/error
- coverage زیرسؤال‌ها
- تعداد source مستقل
- contradiction/staleness
- answerability label
- citation mapping validity

Thresholdها با labeled eval calibrate شوند. Internal score به کاربر نمایش داده نشود؛ outcome شفاف نمایش داده شود.

### 9.6 Answer validation

پیشنهاد contract داخلی structured:

```json
{
  "answer_markdown": "...",
  "claims": [
    {"text": "...", "source_ids": ["chunk-id"]}
  ],
  "follow_up_question": null,
  "suggestions": ["..."],
  "outcome": "answered"
}
```

Backend باید:

- source ID ناشناخته را reject کند؛
- source URL را از database بسازد؛
- claim بدون source را حذف/repair یا کل answer را fail کند؛
- یک repair attempt محدود فقط وقتی evidence کافی است اجرا کند؛
- بعد از repair failure، پاسخ فنی را نمایش ندهد.

---

## 10) Scope، intent و Agentic policy

### 10.1 Intent taxonomy

```text
deploy | configure | connect | troubleshoot | compare
plan_or_cost | account_or_team | explain | locate_docs | out_of_scope
```

Entities:

```text
product, platform, framework, database, version, error_code,
command, desired_outcome, current_step, knowledge_level
```

`knowledge_level` یک سیگنال استنباط‌شده از متن و recent turns است، نه control یا
profile دائمی سمت browser.

### 10.2 Clarification policy

سؤال تکمیلی فقط اگر پاسخ آن یکی از این‌ها را عوض کند:

- سند/محصول هدف
- platform/framework/version
- مسیر public/private network
- error branch
- مرحله‌ی بعد

در هر turn یک سؤال متمرکز. اگر جواب مستقیم ممکن است، اول جواب بده و clarification اختیاری را انتها بگذار.

### 10.3 Model routing

| مسیر | شرایط | مدل |
|---|---|---|
| Policy deterministic | out-of-scope قطعی، rate-limit، support message | بدون LLM |
| Clarification deterministic/small | entity حیاتی مفقود و سؤال روشن | بدون LLM یا small |
| Simple grounded | یک intent، evidence قوی، حداکثر دو سند، context کوتاه | small |
| Complex grounded | چندسندی، چندمرحله‌ای، diagnosis/contradiction | large |
| Insufficient evidence | evidence زیر gate | بدون answer generation |

User مدل را انتخاب نمی‌کند. routing reason و tier در telemetry ثبت می‌شود.

### 10.4 سطح دانش

- سطح توسط مدل از سؤال و context محدود همان session استنباط می‌شود؛ selector دستی
  یا model picker در UI نمایش داده نمی‌شود.
- Beginner: اصطلاح کوتاه توضیح داده شود، مراحل شماره‌دار، command + محل اجرا + نتیجه‌ی موردانتظار.
- Intermediate: توضیح فشرده، command و caveat اصلی.
- Advanced: جزئیات config/edge case، حداقل توضیح بدیهیات.

Facts و citations در هر سه سطح یکسان‌اند؛ فقط presentation depth تغییر می‌کند.

### 10.5 Support state machine

```text
answerable -> answer
ambiguous_and_resolvable -> clarify
not_answerable -> support
first_same_issue_failure -> verified alternative / diagnostic question
second_same_issue_failure -> support_primary + copyable summary
```

Summary تیکت:

- هدف کاربر
- platform/versionهای گفته‌شده
- مراحل مستندی که انجام شده
- error دقیقِ ارائه‌شده توسط کاربر
- sourceهایی که پیشنهاد شده‌اند
- بدون secret و بدون ادعای ساخته‌شده

---

## 11) Session و context

### 11.1 storage

Redis keyها namespace و TTL دارند:

```text
session:{opaque_id}:state
session:{opaque_id}:turns
session:{opaque_id}:idempotency:{message_id}
rate:{scope}:{hashed_identity}:{window}
cache:{corpus_version}:{policy_version}:{key}
```

### 11.2 lifecycle

```text
new -> active -> summarized (optional, still active) -> expired/reset
```

- sliding TTL configurable؛ baseline دو ساعت.
- max turns و max serialized size.
- popup/page یک cookie/session.
- session reset keys مرتبط را حذف می‌کند.
- browser فقط message جاری و opaque ID را می‌فرستد؛ history کامل منبع حقیقت نیست.

### 11.3 factual summary

Summary فقط موارد زیر را نگه دارد:

- goal کاربر
- platform/product/version صریح
- knowledge level
- completed/failed steps
- unresolved question

Summary نباید پاسخ قبلی مدل را بدون source به fact تبدیل کند. source IDs یا corpus version برای facts فنی حفظ شوند.

---

## 12) Streaming contract

Browser از `useChat` و transport صریح به `/api/chat` استفاده می‌کند. Next adapter به FastAPI `/v1/chat/stream` وصل می‌شود.

### Request

```json
{
  "protocol_version": "1",
  "session_id": "opaque",
  "message_id": "idempotency-key",
  "text": "متن کاربر",
  "surface": "popup",
  "locale": "fa-IR"
}
```

### Events

```text
message_start
status                # کوتاه و امن؛ نه chain-of-thought
text_delta
sources               # metadata validated
suggestions
support
usage                 # tier/token/cache, non-sensitive
message_end
error
```

### خطاها

| HTTP/code | رفتار UI |
|---|---|
| 400/422 invalid_input | input حفظ شود، پیام اصلاح |
| 409 duplicate | generation دوم شروع نشود |
| 429 rate_limited | Retry-After، بدون retry loop |
| 503 provider_unavailable | retry کنترل‌شده |
| 504 timeout | پیام روشن و یک retry دستی |
| grounding_failed | answer حذف، clarification/support |

Stop باید request FastAPI و provider stream را abort کند و token usage را تا حد ممکن متوقف سازد.

---

## 13) UI state matrix

| State | Popup | Page | اقدام کاربر |
|---|---|---|---|
| Welcome | معرفی + starters | معرفی گسترده‌تر + categories | انتخاب starter/نوشتن |
| Submitted | composer disabled + status | همان | Stop |
| Streaming | answer incremental، stable scroll | فضای خواندن بیشتر | Stop/scroll |
| Ready | sources + suggestions | sources/card یا supporting pane | follow-up/Copy |
| Low evidence | clarification یا Support card | همان با توضیح بیشتر | پاسخ/تیکت |
| Repeated failure | Ticket CTA primary | summary قابل‌کپی | Ticket/Copy |
| Offline | input حفظ | input حفظ | retry پس از اتصال |
| Rate limited | زمان retry | زمان retry | wait |
| Provider error | context حفظ | context حفظ | retry دستی |

### Code rendering acceptance

- language label از fence؛ fallback `Text`.
- Bash/Python/JavaScript/TypeScript/JSON/YAML fixture.
- Copy فقط content، نه شماره خط/label.
- LTR، horizontal scroll، selection و mobile touch.
- Copy success/error accessible feedback.

### Responsive acceptance

- 320px: launcher و composer قابل‌استفاده؛ popup تقریباً full-screen.
- 375px: source cards stack؛ code overflow داخلی.
- 768px: bounded layout و touch/keyboard مناسب.
- 1024px: full page centered؛ supporting pane اختیاری.
- 1440px: line length کنترل؛ conversation بیش‌ازحد کشیده نشود.

---

## 14) Security threat model خلاصه

### Threat: Prompt injection از user

کنترل: role allowlist، system/data separation، no client history authority، output validator.

### Threat: Prompt injection داخل docs

کنترل: corpus untrusted، parser/redactor، delimiters، source-only claims، injection eval.

### Threat: Source spoofing

کنترل: source IDs backend-only، URL metadata allowlist، model URL ignored.

### Threat: Secret leakage

کنترل: env/secret manager، redaction corpus/log، secret scan، no raw prompt logging.

### Threat: Cost abuse / DoS

کنترل: distributed rate limit، size/token caps، concurrency/bulkhead، deterministic reject، idempotency.

### Threat: XSS و unsafe Markdown

کنترل: sanitization، no raw HTML، safe link policy، CSP، dependency review.

### Threat: Session fixation/cross-session leak

کنترل: opaque IDs، secure cookie، rotation/reset، ownership، TTL، isolation tests.

### Threat: Retry storms/provider outage

کنترل: max retry، exponential backoff+jitter، circuit breaker، `Retry-After`، no automatic UI loop.

---

## 15) Monitoring و quality telemetry

### 15.1 Structured logs

فیلدهای پیشنهادی:

```text
timestamp, level, service, environment, request_id,
session_hash, route, outcome, error_code,
corpus_version, intent, model_tier, provider,
retrieval_ms, rerank_ms, ttft_ms, total_ms,
input_tokens, output_tokens, cached_tokens, cache_hit
```

متن خام user، prompt، chunks، IP و credential پیش‌فرض log نشود.

### 15.2 Metrics

- request/error/latency/TTFT/stream abort
- retrieval empty/low confidence/recall sample/reranker timeout
- answered/clarified/no-answer/support/out-of-scope
- citation count/invalid mapping/claim validation failure
- small/large routing و token/cost
- cache hit/miss/stale rejection
- rate limit و active session

### 15.3 Tracing

Spanها:

```text
http.request
session.load
intent.classify
retrieval.vector
retrieval.lexical
retrieval.rerank
evidence.evaluate
provider.generate
answer.validate
stream.write
session.commit
```

Attributes حساس یا متن کامل ممنوع. OpenTelemetry exporter configurable و Sentry اختیاری.

### 15.4 Alertها

- provider 5xx/timeout spike
- readiness failure
- p95 TTFT/latency breach
- citation validation failure > 0
- no-answer/support rate deviation
- large-model share یا daily cost anomaly
- rate-limit surge

---

## 16) Cost engineering

1. out-of-scope و policy response بدون مدل.
2. small model default برای evidence قوی.
3. large model فقط با reason code.
4. history bounded + factual summary.
5. chunk dedupe و dynamic top-k.
6. output cap بر intent/skill level.
7. embedding incremental و batch.
8. cache key شامل corpus/policy version و level.
9. cache فقط پاسخ validated؛ session-specific response با احتیاط.
10. abort واقعی و عدم retry غیرضروری.
11. dashboard token/cost و budget alert.

در هر optimization، quality gate باید ثابت بماند. کاهش هزینه‌ای که citation/accuracy را پایین بیاورد پذیرفته نیست.

---

## 17) Test strategy

### 17.1 Unit

- Persian normalization بدون تخریب code/version
- canonical URL parser و relative link resolver
- redaction secrets
- heading/code-aware chunking
- RRF/dedup/routing/token budget/cache key
- issue failure counter
- citation mapping/output validator

### 17.2 Integration

- ingest نمونه‌های واقعی از همه‌ی docs areas
- Postgres/Pgvector exact/IVFFlat behavior
- Redis TTL/session/rate/idempotency
- provider stream/abort/usage/error mapping
- corpus activation/rollback

### 17.3 Contract

- FastAPI OpenAPI -> frontend types
- event order/schema و error status
- Next adapter -> AI SDK UI parts
- source cards فقط با metadata معتبر

### 17.4 E2E

- Welcome starter تا answer/source
- Popup -> Page با session مشترک
- follow-up و knowledge level
- code Copy برای زبان‌های هدف
- Stop و duplicate prevention
- ambiguity و clarification
- no-answer/out-of-scope
- دو شکست -> Ticket
- 429/503/504/offline
- responsive و keyboard

### 17.5 RAG eval

Dataset versioned با سؤال‌های ساده، پیچیده، چندمرحله‌ای، typo، follow-up، unknown، injection و contradiction. Gateها در `spec.md` تعریف شده‌اند.

LLM judge به‌تنهایی کافی نیست. deterministic fact/source checks + human sample review لازم است.

### 17.6 Security/load/deployment

- XSS/CORS/origin/cookie/oversized input
- prompt/corpus injection و source spoof
- secret/dependency scan
- concurrent streams، provider outage، retry storm
- production build، migration، live/ready، smoke، rollback

---

## 18) استقرار روی Liara

### 18.1 topology

- یک Next.js app برای frontend
- یک Python/FastAPI app برای backend
- PostgreSQL با Pgvector فعال
- Redis
- private network میان backend/database/Redis و در صورت امکان frontend/backend
- provider AI با baseURL و key در Environment Variables

### 18.2 Frontend

پروژه باید واقعاً با `create-next-app` ساخته شود، چون مستندات Next.js Liara این شرط را بیان کرده‌اند. `package.json` استاندارد، build production و `liara.json` مطابق docs current.

### 18.3 Backend

FastAPI روی host `0.0.0.0` و port محیط/پلتفرم bind شود. مستندات فعلی نمونه‌ی deploy پایتون را با `liara deploy --port 80 --platform python` ارائه می‌کند؛ command نهایی را با ساختار واقعی app و docs current verify کن.

### 18.4 Database/Redis

- private connection strings فقط env.
- Pgvector enable پیش از migration.
- connection pool limits متناسب با plan.
- HNSW ممنوع مگر Liara بعداً رسماً پشتیبانی کند و re-verify شود.
- backup/restore و migration rollback مستند.

### 18.5 Health و zero-downtime

- liveness سبک و مستقل.
- readiness شامل dependency و active corpus.
- Liara health check به endpoint درست وصل شود.
- startup period متناسب با migration/index load.
- traffic فقط پس از readiness/smoke.

### 18.6 Staging checklist

1. secrets و CORS origins
2. migrations + corpus ingestion
3. ready/live
4. سؤال grounded ساده
5. سؤال پیچیده
6. no-answer و Ticket
7. session continuation popup/page
8. rate limit
9. monitoring trace/log/metric
10. cost/token record
11. rollback drill

---

## 19) نقشه‌ی اجرا و commitها

### Phase 0 — Discovery و baseline

- audits، ADR و compatibility matrix
- Git init/identity/secret policy
- eval taxonomy اولیه

Commitهای نمونه:

```text
docs: record legacy chatbot and Liara corpus discovery
docs: define system boundaries and compatibility baseline
```

### Phase 1 — Project scaffolding

- Next/FastAPI واقعی
- shadcn RTL و AI Elements
- settings، health، lint/type/test/build

```text
chore: scaffold Next.js and FastAPI applications
feat: establish RTL design system and chat primitives
```

### Phase 2 — Ingestion vertical slice

- parse/redact/chunk/version
- Postgres schema/Pgvector
- ingest چند سند واقعی و سپس کل corpus

```text
feat: ingest versioned Liara documentation corpus
test: cover Persian normalization and safe chunking
```

### Phase 3 — Retrieval و eval

- lexical/vector/RRF/reranker
- golden dataset و baseline report

```text
feat: add hybrid retrieval and evidence ranking
test: add grounded retrieval evaluation suite
```

### Phase 4 — API model و grounded answers

- provider adapter، router، prompts، validator، citations
- no-answer/out-of-scope

```text
feat: stream grounded answers through API model router
feat: validate citations and support fallbacks
```

### Phase 5 — Session/Agentic

- Redis session، summary، level، multi-step، repeated failure

```text
feat: persist bounded session context and issue state
feat: add clarification and support escalation policy
```

### Phase 6 — UI completion

- Popup/Page shared shell، source cards، code Copy، all states، responsive/a11y

```text
feat: deliver shared popup and full-page chat experience
test: cover responsive accessible chat flows
```

### Phase 7 — Hardening/observability/cost

- rate limit، circuit breaker، logs/metrics/traces، cache/token budgets

```text
feat: enforce distributed limits and token budgets
feat: instrument quality reliability and cost telemetry
```

### Phase 8 — Liara staging/production readiness

- config/migrations/health/smoke/rollback/runbooks

```text
chore: prepare Liara deployment and rollback runbooks
test: verify production deployment smoke suite
```

هر commit فقط بعد از checks مرتبط. عبارت «همه‌ی تغییرات commit شوند» مجوز commit secret، artifact خراب یا تغییر نامرتبط نیست.

---

## 20) Quality gates پیش از اعلام پایان

### پاسخ و RAG

- critical hallucination صفر
- source URL validity صددرصد
- claim support و citation precision حداقل 95%
- no-answer/out-of-scope recall حداقل 95%
- release eval report versioned

### UI

- Popup/Page و shared session
- 320/375/768/1024/1440
- code Copy و labels
- no blank initial state
- zero serious/critical automated accessibility issue
- keyboard manual pass

### Agentic

- clarification فقط وقتی لازم
- context طولانی bounded
- level adaptation
- same-issue repeated failure -> Support

### Security/operations

- distributed rate limit
- no committed secrets
- typed errors/statuses
- provider outage/timeout behavior
- structured logs/metrics/traces/alerts

### Deployment/cost

- Liara build/migration/health/smoke/rollback pass
- small/large routing eval
- token caps/cache versioning
- cost dashboard/alert

---

## 21) ممنوعیت‌های صریح برای ایجنت Vibe Coding

- شروع feature قبل از audit دو repository
- کپی کور کد یا prompt چت‌بات قبلی
- استفاده از OpenRack data در پاسخ Liara
- پاسخ بدون source، URL ساخته‌شده توسط مدل یا citation جعلی
- local model/Ollama در production path
- نگهداری history کامل فقط در browser
- مدل‌دادن برای out-of-scope قطعی
- افزودن mock response به runtime برای «کامل نشان‌دادن» UI
- hard-code model ID، API key، timeout، ticket contact یا price
- قرار دادن passphrase/root password در file/command/log
- نمایش chain-of-thought
- نصب همه‌ی shadcn components بدون نیاز
- فرض HNSW روی PostgreSQL لیارا
- اعلام completion بدون test/eval/build/deployment evidence

---

## 22) اولین دستور به ایجنت اجراکننده

> ابتدا `AGENTS.md`، `agent.md`، `spec.md` و skillهای مرتبط را کامل بخوان. سپس repository رسمی مستندات Liara در `/home/mohuva/Desktop/hackaton/docs/` و چت‌بات قبلی در `/home/mohuva/Desktop/hackaton/LLM-OpenRack/` را مطابق بخش Discovery این سند به‌صورت end-to-end و corpus-wide بررسی کن. یافته‌ها، تناقض‌ها، counts و تصمیم‌ها را در audit/ADR ثبت و commit کن. تا پیش از قبولی discovery، compatibility و security gates هیچ کد محصولی نساز. پس از آن vertical sliceهای واقعی را مرحله‌به‌مرحله، همراه test/eval/observability و commit پیاده کن؛ هیچ پاسخ، source یا integration جعلی در production path مجاز نیست.
