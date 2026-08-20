# Ingestion baseline

Snapshot: 2026-08-21
Docs commit: `dbb7430b1abc5bf92ccca3538f45c54bdc632fa8`

The production ingestion source is `/home/mohuva/Desktop/hackaton/docs/public/llms/**/*.md`. A dry run of the implemented parser, redactor, structural chunker, and manifest builder produced:

| Metric | Result |
|---|---:|
| Markdown files discovered | 1,143 |
| Documents accepted | 1,142 |
| Documents safely skipped | 1 |
| Parse failures | 0 |
| Structural chunks | 1,983 |
| Credential-like example values redacted | 181 |

The skipped file is `public/llms/ai/ai-sdk-errors/ai-api-call-error.md`. It has a canonical URL but contains converter instructions and no level-one title or substantive document content; activating it would index prompt-like navigation noise.

Three generated Markdown files contain mechanically malformed fences. The parser repairs an unclosed language-qualified fence at EOF and ignores a trailing empty closing marker. Tests ensure repaired code remains an atomic chunk. The source checkout is not modified.

Canonical URLs are accepted only when they use HTTPS and the exact `docs.liara.ir` hostname. The manifest hash covers the sorted source path and processed content hash. Re-ingesting the same source commit and manifest resolves to the existing corpus version.

The initial migration enables Pgvector and pg_trgm but deliberately creates no HNSW index. Exact vector search is the baseline; IVFFlat remains gated on a real recall/latency benchmark.
