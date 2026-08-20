# Liara Documentation Assistant

زیرساخت مهندسی و قراردادهای پیش از توسعه‌ی چت‌بات مستندات رسمی لیارا.

## از کجا شروع کنیم؟

1. [AGENTS.md](./AGENTS.md) — قواعد اجرایی و Definition of Done برای ایجنت‌ها
2. [agent.md](./agent.md) — پاسخ What / Why / How و مرزهای محصول
3. [spec.md](./spec.md) — مشخصات محصول، نیازمندی‌ها و معیارهای پذیرش
4. [VIBE_CODING_BRIEF.md](./VIBE_CODING_BRIEF.md) — نقشه‌ی جامع معماری، پیاده‌سازی، تست و استقرار
5. [skillهای پروژه](./.agents/skills) — قراردادهای Material 3، shadcn/ui و AI chat UI

این مخزن در این مرحله عمداً کد نمایشی یا پاسخ mock ندارد. توسعه‌ی محصول باید پس از discovery اجباری دو مخزن مرجع آغاز شود:

- مستندات رسمی لیارا: `/home/mohuva/Desktop/hackaton/docs/`
- چت‌بات قبلی: `/home/mohuva/Desktop/hackaton/LLM-OpenRack/`

رمز، API key، passphrase و اطلاعات دسترسی نباید در Git ذخیره شوند. فقط نام متغیرها در `.env.example` نگهداری می‌شود و مقدار واقعی در تنظیمات Secret/Environment لیارا قرار می‌گیرد.
