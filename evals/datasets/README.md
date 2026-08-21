# Taxonomy اولیه‌ی ارزیابی

هر case نسخه‌دار باید این فیلدها را داشته باشد:

```text
id, turns, expected_intent, expected_docs, forbidden_docs,
answerable, required_facts, forbidden_claims, expected_outcome,
audience_cues, tags
```

پوشش اجباری dataset:

- همه‌ی حوزه‌های top-level corpus و Console/CLI/API/Team
- سؤال مستقیم، پیچیده، چندسندی و چندمرحله‌ای
- typo، ی/ک و رقم فارسی/عربی، error code و version
- follow-up، reference resolution و session isolation
- ambiguity واقعی و over-clarification negative cases
- no-answer، out-of-scope، conflicting/stale docs
- prompt injection از query و corpus و source spoofing
- repeated same-issue failure و topic change
- code-heavy و citation mapping

gateهای کمی در `spec.md` منبع حقیقت‌اند. dataset واقعی در vertical slice retrieval ساخته می‌شود و هیچ query production از fixture پاسخ نمی‌گیرد.
