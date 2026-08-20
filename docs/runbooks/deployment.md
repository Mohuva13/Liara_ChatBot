# استقرار و rollback روی لیارا

Frontend و backend دو برنامهٔ جدا هستند. frontend روی پلتفرم Next.js و backend روی پلتفرم Docker اجرا می‌شود. PostgreSQL/Pgvector، Redis و هر دو برنامه باید در یک شبکهٔ خصوصی قرار بگیرند.

## ترتیب انتشار

1. PostgreSQL و Redis را بسازید و شبکهٔ خصوصی را متصل کنید.
2. Secretهای backend را در Environment لیارا تنظیم کنید؛ کلید provider در frontend ممنوع است.
3. backend را از مسیر `backend/` با `backend/liara.json` منتشر کنید.
4. ingestion را به‌عنوان job کنترل‌شده اجرا و فقط نسخهٔ verifyشده را activate کنید.
5. `/health/live` و `/health/ready` را بررسی کنید.
6. `API_INTERNAL_BASE_URL` frontend را روی آدرس خصوصی backend تنظیم کنید.
7. frontend را از مسیر `frontend/` منتشر کنید و smoke test Page/Popup را انجام دهید.

فایل‌های `liara.json` عمداً `app` و `platform` ندارند تا با استقرار GitHub تضاد نداشته باشند. شناسه و platform در Console/CLI انتخاب می‌شوند.

## rollback

- برنامه: از تاریخچهٔ استقرار لیارا به release قبلی بازگردید.
- corpus: `activated_at` نسخهٔ قبلی را در یک transaction بازگردانید؛ chunkهای نسخهٔ جدید حذف نمی‌شوند تا rollback قابل بازیابی بماند.
- provider: مدل/endpoint قبلی را در Environment برگردانید و readiness + smoke query را تکرار کنید.
- هر rollback باید correlation ID، release، corpus version و علت را ثبت کند.

منابع رسمی: `https://docs.liara.ir/paas/nextjs/quick-start/`، `https://docs.liara.ir/paas/docker/how-tos/deploy-app/` و `https://docs.liara.ir/paas/liarajson/`.
