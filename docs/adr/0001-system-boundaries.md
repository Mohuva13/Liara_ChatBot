# ADR-0001: مرزهای سیستم و مالکیت اعتماد

- وضعیت: Accepted
- تاریخ: 2026-08-21
- تصمیم‌گیر: baseline پروژه Liara Documentation Assistant

## زمینه

محصول دو surface (Popup و صفحه Chat) دارد، اما باید یک conversation و policy مشترک داشته باشد. AI SDK UI در frontend از transport استریمی استفاده می‌کند و FastAPI backend الزام معماری است. corpus رسمی untrusted data محسوب می‌شود و URL یا history ارسالی browser نمی‌تواند مرجع حقیقت باشد.

## تصمیم

```text
Browser (Popup/Page, one session)
  -> Next.js same-origin /api/chat adapter
  -> FastAPI /v1/chat/stream
      -> Redis: session, idempotency, limit, issue state, cache
      -> PostgreSQL/Pgvector: active corpus, chunks, metadata, vectors
      -> provider adapters: embeddings/generation
  <- validated text parts + server-built sources + suggestions/support
```

### Browser

- مالک input، rendering، local interaction state، Stop، Copy و navigation است.
- فقط پیام جاری و شناسه opaque/session cookie را می‌فرستد؛ history کامل مرجع حقیقت نیست.
- provider key، DSN، prompt policy، chunk خام یا source mapping دریافت نمی‌کند.
- Popup و Page از یک ChatProvider/ChatShell و session مشترک استفاده می‌کنند.

### Next.js adapter

- route هم‌مبدأ برای cookie/origin و تبدیل stream FastAPI به AI SDK UI message protocol است.
- business logic مربوط به RAG، session، confidence، model routing یا citation را تکرار نمی‌کند.
- خطا و abort را بدون retry loop به backend/upstream propagate می‌کند.

### FastAPI

- مرجع حقیقت session/history، scope/intent، retrieval، evidence sufficiency، escalation، rate/cost policy و provider calls است.
- URL citation را فقط از metadata allowlisted می‌سازد؛ URL تولیدشده توسط مدل پذیرفته نمی‌شود.
- retrieved text را untrusted data می‌داند و claim بدون source معتبر را نمایش نمی‌دهد.
- status code واقعی و error code پایدار برمی‌گرداند.

### PostgreSQL/Pgvector و Redis

- PostgreSQL نسخه‌های corpus، document/chunk metadata، vector و activation/rollback را نگه می‌دارد.
- به‌دلیل محدودیت رسمی Liara، HNSW انتخاب نمی‌شود؛ exact/IVFFlat benchmark می‌شوند.
- Redis stateهای کوتاه‌عمر و distributed را با namespace و TTL نگه می‌دارد.

### Provider

- پشت interface async/configurable قرار دارد؛ model ID، URL، timeout و token cap از settings می‌آیند.
- browser هرگز مستقیم provider را صدا نمی‌زند.
- usage، finish reason، abort و typed transient/permanent errors بخشی از interface هستند.

## قرارداد trust

1. user text، browser metadata و corpus text داده‌اند، نه instruction سیستمی.
2. session server-issued و bounded است؛ forged roles/history رد یا نادیده گرفته می‌شوند.
3. پاسخ فنی فقط پس از evidence sufficiency و claim/source validation stream می‌شود.
4. clarification، out-of-scope و Support می‌توانند deterministic و بدون model باشند.
5. production path از mock/fixture، OpenRack corpus یا local Ollama استفاده نمی‌کند.

## پیامدها

مثبت:

- یک policy واحد برای هر دو surface و امکان تست contract مستقل.
- secretها server-side و citationها by construction می‌مانند.
- provider/UI بدون جابه‌جایی ownership قابل‌تعویض‌اند.

هزینه‌ها:

- adapter stream و contract test اضافی لازم است.
- Redis/PostgreSQL برای development integration باید فراهم شوند.
- readiness از liveness جدا و تا نبود dependency/corpus فعال fail می‌ماند.

## گزینه‌های ردشده

- تماس مستقیم browser با provider: secret و policy را افشا می‌کند.
- RAG داخل Next route: ownership را دوپاره و FastAPI را دور می‌زند.
- اعتماد به history browser: session fixation/forgery و context بی‌حد ایجاد می‌کند.
- URL citation توسط مدل: validity و allowlist را تضمین نمی‌کند.
- HNSW پیش‌فرض: با محدودیت مستند PostgreSQL لیارا سازگار نیست.
