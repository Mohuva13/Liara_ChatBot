import argparse
import asyncio
import json
import re
import subprocess
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.ingestion.models import IngestionConfig
from app.ingestion.pipeline import ingest_corpus, scan_corpus, snapshot_report
from app.providers.openai_compat import OpenAICompatibleProvider
from app.providers.resilient import ProviderTarget, ResilientProvider

COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


def _validate_commit(value: str) -> str:
    commit = value.strip()
    if not COMMIT_SHA.fullmatch(commit):
        raise RuntimeError("documentation source commit is not a full Git SHA")
    return commit.lower()


def _git_directory(docs_root: Path) -> Path:
    marker = docs_root / ".git"
    if marker.is_dir():
        return marker
    if marker.is_file():
        content = marker.read_text(encoding="utf-8").strip()
        if not content.startswith("gitdir: "):
            raise RuntimeError("invalid documentation .git file")
        git_dir = Path(content.removeprefix("gitdir: ").strip())
        return git_dir if git_dir.is_absolute() else (docs_root / git_dir).resolve()
    raise RuntimeError("documentation checkout has no Git metadata")


def _commit_from_git_metadata(docs_root: Path) -> str:
    git_dir = _git_directory(docs_root)
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return _validate_commit(head)

    target_ref = head.removeprefix("ref: ").strip()
    loose_ref = git_dir / target_ref
    if loose_ref.is_file():
        return _validate_commit(loose_ref.read_text(encoding="utf-8"))

    packed_refs = git_dir / "packed-refs"
    if packed_refs.is_file():
        for line in packed_refs.read_text(encoding="utf-8").splitlines():
            if line.startswith(("#", "^")):
                continue
            commit, _, ref = line.partition(" ")
            if ref == target_ref:
                return _validate_commit(commit)
    raise RuntimeError(f"cannot resolve documentation Git ref: {target_ref}")


def source_commit(docs_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=docs_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return _validate_commit(result.stdout)
    except (FileNotFoundError, subprocess.SubprocessError):
        return _commit_from_git_metadata(docs_root)


async def run() -> None:
    parser = argparse.ArgumentParser(description="Ingest official Liara documentation")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    config = IngestionConfig(
        docs_root=settings.docs_repo_path,
        embedding_batch_size=settings.embedding_batch_size,
    )
    commit = source_commit(settings.docs_repo_path)

    if args.dry_run:
        snapshot = scan_corpus(config, commit)
        print(json.dumps(snapshot_report(snapshot), ensure_ascii=False, indent=2))
        return
    if settings.database_url is None:
        raise SystemExit("DATABASE_URL is required for ingestion")
    if not all(
        (
            settings.embedding_base_url,
            settings.embedding_api_key,
            settings.embedding_model,
            settings.embedding_dimensions,
        )
    ):
        raise SystemExit("embedding provider configuration is required for ingestion")
    assert settings.embedding_api_key is not None
    assert settings.embedding_base_url is not None
    assert settings.embedding_model is not None
    assert settings.embedding_dimensions is not None
    targets = [
        ProviderTarget(
            "primary",
            OpenAICompatibleProvider(
                base_url=str(settings.embedding_base_url),
                api_key=settings.embedding_api_key.get_secret_value(),
                timeout_seconds=settings.embedding_request_timeout_seconds,
                max_retries=settings.llm_max_retries,
            ),
        )
    ]
    if settings.embedding_backup_api_key is not None:
        targets.append(
            ProviderTarget(
                "backup",
                OpenAICompatibleProvider(
                    base_url=str(
                        settings.embedding_backup_base_url
                        or settings.embedding_base_url
                    ),
                    api_key=settings.embedding_backup_api_key.get_secret_value(),
                    timeout_seconds=settings.embedding_request_timeout_seconds,
                    max_retries=settings.llm_max_retries,
                ),
            )
        )
    provider = ResilientProvider(
        targets,
        failure_threshold=settings.provider_circuit_failure_threshold,
        reset_seconds=settings.provider_circuit_reset_seconds,
        concurrency_limit=settings.provider_concurrency_limit,
        queue_timeout_seconds=settings.provider_queue_timeout_seconds,
    )
    try:
        version_id, snapshot = await ingest_corpus(
            config,
            commit,
            settings.database_url.get_secret_value(),
            Path(__file__).parents[2] / "migrations",
            provider,
            settings.embedding_model,
            settings.embedding_dimensions,
            activate=args.activate,
        )
    finally:
        await provider.aclose()
    report = snapshot_report(snapshot)
    report["version_id"] = version_id
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(run())
