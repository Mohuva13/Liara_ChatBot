# ممیزی چت‌بات قدیمی OpenRack

تاریخ snapshot: ۱۴۰۵/۰۵/۳۰ (2026-08-21)  
Repository: `/home/mohuva/Desktop/hackaton/LLM-OpenRack`  
Branch: `main`  
Commit: `295501e20c3e96f0c02f184046280c4815c0f302`

## دامنه و روش بررسی

جریان `/recommend` از ورودی HTTP تا Rule Engine، RAG، Prompt Builder، LLM Client، Post Processor و Confidence Engine مستقیم خوانده شد. همه‌ی فایل‌های `app/`، مدل‌های داده، دو فایل JSON، تست‌ها، dependencyها، READMEها و اسکریپت‌های عملیاتی نیز بررسی شدند.

فرمان‌های بازتولیدپذیر اصلی:

```bash
git -C /home/mohuva/Desktop/hackaton/LLM-OpenRack status --short --branch
git -C /home/mohuva/Desktop/hackaton/LLM-OpenRack rev-parse HEAD
rg --files /home/mohuva/Desktop/hackaton/LLM-OpenRack
PYTHONDONTWRITEBYTECODE=1 python3 verify_patch.py
PYTHONDONTWRITEBYTECODE=1 python3 test_postprocessor_final.py
```

هر دو validation موجود در snapshot پاس شدند. این تست‌ها فقط syntax، ساختار ۴۵ رکورد Knowledge Base و رفتار Post Processor را پوشش می‌دهند؛ صحت RAG یا grounding را ثابت نمی‌کنند.

## جریان واقعی سیستم

```text
POST /recommend
  -> ترکیب پیام فعلی با تمام پیام‌های user ارسالی browser
  -> RuleEngine.analyze
  -> HybridRAG.search در thread pool، semaphore=3
  -> PromptBuilder با حداکثر ۸ پیام history
  -> LLMClient.generate در thread pool، semaphore=1
  -> PostProcessor.process
  -> ConfidenceEngine.evaluate
  -> پاسخ JSON
```

- FastAPI دو endpoint عمومی `/recommend` و `/health` دارد.
- `HybridRAG` هنگام import برنامه ساخته می‌شود و مدل embedding و دو FAISS index را در startup بارگذاری می‌کند.
- Hardware corpus دارای ۳۹ رکورد است: ۲۹ GPU، ۶ CPU و ۴ Storage.
- Knowledge Base دارای ۴۵ رکورد یکتا در ۲۴ دسته است.
- مدل `all-MiniLM-L6-v2` یک بار بارگذاری می‌شود و embedding یک query میان دو جست‌وجو reuse می‌شود.
- جست‌وجوی hardware ابتدا constraintهای rule-based را اعمال و سپس FAISS L2 را رتبه‌بندی می‌کند.
- جست‌وجوی knowledge ترکیبی از FAISS cosine، alias، keyword، token coverage، Jaccard و SequenceMatcher است و gate ثابت `0.34` دارد.
- roleها normalize می‌شوند؛ نقش ناشناخته یا `system` ارسالی client به `user` تبدیل می‌شود.
- prompt، user/history/hardware/knowledge را در delimiterهای جدا و به‌عنوان data معرفی می‌کند.
- client همگام provider سه retry با delay خطی دارد؛ timeout، URL و model در کد ثابت‌اند.

## الگوهای قابل‌حفظ با بازطراحی

| الگو | ارزش | تصمیم برای Liara |
|---|---|---|
| نرمال‌سازی ی/ک، ارقام و نیم‌فاصله | recall بهتر query فارسی | با جداسازی display/search copy و محافظت از code/URL/version بازنویسی و unit-test شود |
| retrieval واژگانی + معنایی | exact term و paraphrase را پوشش می‌دهد | با PostgreSQL/Pgvector، lexical مستقل و RRF پیاده شود |
| reuse یک query embedding | latency/cost کمتر | در pipeline جدید حفظ شود |
| role allowlist | کاهش forged system history | browser فقط پیام جاری را می‌فرستد؛ server history مرجع حقیقت می‌شود |
| جداسازی data از system instruction | مرز اولیه در برابر injection | corpus همچنان untrusted و output validation اجباری باشد |
| concurrency gate و retry concept | جلوگیری از overload | distributed/bounded، async، با jitter، typed errors و retry budget بازطراحی شود |
| خروجی ساخت‌یافته و fallback | قابلیت تست policy | contract جدید claim/source-aware و confidence کالیبره باشد |

## ریسک‌ها و بدهی‌های قطعی

1. **Critical — credential leakage:** چند اسکریپت عملیاتی repository، credential و target عملیاتی را به‌صورت plaintext و committed نگه می‌دارند. مقدارها عمداً در این audit ثبت نشده‌اند. هیچ‌یک از این فایل‌ها یا داده‌ها نباید کپی شوند و credentialهای مربوط باید خارج از این پروژه rotate شوند.
2. **Critical — claim خارج از evidence:** Post Processor عمداً نام GPU/CPU ذکرشده توسط مدل را حتی اگر در RAG نباشد می‌پذیرد. این رفتار برای دستیار Liara ممنوع است.
3. **High — client-authoritative history:** browser تمام history را می‌فرستد؛ backend session store، ownership، TTL یا isolation ندارد.
4. **High — confidence نامعتبر:** امتیاز ۴۰٪ rule، ۴۰٪ retrieval و ۲۰٪ «خالی نبودن متن مدل» است. threshold کد `0.45` است، در حالی که README اصلی `0.6` را ادعا می‌کند.
5. **High — HTTP semantics:** خطای provider و low-confidence با HTTP 200 برمی‌گردند؛ client نمی‌تواند failure class را درست تشخیص دهد.
6. **High — hard-coded runtime:** provider محلی، model ID، URL، timeout و fallback تماس در کد ثابت‌اند.
7. **High — secret/PII logging:** `print` بخشی از response body provider و exception را ثبت می‌کند.
8. **Medium — retry storm:** retry برای همه‌ی exceptionهاست، jitter، idempotency، circuit breaker یا تفکیک transient/permanent ندارد.
9. **Medium — startup coupling:** import برنامه download/load مدل و ساخت index را trigger می‌کند؛ liveness و readiness از هم جدا نیستند.
10. **Medium — mutable default:** `RecommendResponse.alternatives` از `[]` به‌عنوان default استفاده می‌کند.
11. **Medium — incomplete tests:** citation، session، rate limit، security، provider contract، retrieval quality، API status و E2E پوشش ندارند.
12. **Medium — response contract gaps:** `summary_fa` همیشه خالی، `storage/network` ساختگی و ثابت، و source/citation غایب است.

## تصمیم

هیچ کد یا داده‌ی OpenRack وارد production path دستیار Liara نمی‌شود. فقط patternهای جدول بالا، مستقل و با تست‌های requirementهای `spec.md` بازطراحی می‌شوند. corpus پاسخ صرفاً repository رسمی مستندات Liara است.
