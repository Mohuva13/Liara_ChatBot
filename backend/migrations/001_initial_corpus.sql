BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS corpus_versions (
    id uuid PRIMARY KEY,
    source_commit text NOT NULL,
    manifest_hash text NOT NULL,
    status text NOT NULL CHECK (
        status IN ('discovered', 'parsed', 'embedded', 'indexed', 'evaluated', 'active', 'failed')
    ),
    stats jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    activated_at timestamptz,
    UNIQUE (source_commit, manifest_hash)
);

CREATE TABLE IF NOT EXISTS documents (
    version_id uuid NOT NULL REFERENCES corpus_versions(id) ON DELETE CASCADE,
    stable_id text NOT NULL,
    source_path text NOT NULL,
    canonical_url text NOT NULL CHECK (
        canonical_url LIKE 'https://docs.liara.ir/%'
    ),
    title text NOT NULL,
    content_hash text NOT NULL,
    language text NOT NULL DEFAULT 'fa',
    PRIMARY KEY (version_id, stable_id),
    UNIQUE (version_id, source_path),
    UNIQUE (version_id, canonical_url)
);

CREATE TABLE IF NOT EXISTS chunks (
    version_id uuid NOT NULL,
    document_id text NOT NULL,
    stable_id text NOT NULL,
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    heading_path text[] NOT NULL DEFAULT '{}',
    content text NOT NULL,
    normalized_content text NOT NULL,
    content_hash text NOT NULL,
    token_count integer NOT NULL CHECK (token_count > 0),
    code_languages text[] NOT NULL DEFAULT '{}',
    embedding vector,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple', normalized_content)
    ) STORED,
    PRIMARY KEY (version_id, stable_id),
    FOREIGN KEY (version_id, document_id)
        REFERENCES documents(version_id, stable_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS chunks_document_idx
    ON chunks (version_id, document_id, ordinal);
CREATE INDEX IF NOT EXISTS chunks_search_idx
    ON chunks USING gin (search_vector);
CREATE INDEX IF NOT EXISTS chunks_trgm_idx
    ON chunks USING gin (normalized_content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS corpus_versions_active_idx
    ON corpus_versions (activated_at DESC) WHERE activated_at IS NOT NULL;

-- No HNSW index: Liara's current Pgvector service documentation says it is unsupported.
-- Exact vector search is the baseline. IVFFlat is created only by a benchmarked migration.

COMMIT;
