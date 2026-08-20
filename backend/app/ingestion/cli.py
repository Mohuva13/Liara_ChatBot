import argparse
import asyncio
import json
import subprocess
from pathlib import Path

from app.core.config import get_settings
from app.ingestion.models import IngestionConfig
from app.ingestion.pipeline import ingest_corpus, scan_corpus, snapshot_report


def source_commit(docs_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=docs_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


async def run() -> None:
    parser = argparse.ArgumentParser(description="Ingest official Liara documentation")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    config = IngestionConfig(docs_root=settings.docs_repo_path)
    commit = source_commit(settings.docs_repo_path)

    if args.dry_run:
        snapshot = scan_corpus(config, commit)
        print(json.dumps(snapshot_report(snapshot), ensure_ascii=False, indent=2))
        return
    if settings.database_url is None:
        raise SystemExit("DATABASE_URL is required for ingestion")
    version_id, snapshot = await ingest_corpus(
        config,
        commit,
        settings.database_url.get_secret_value(),
        Path(__file__).parents[2] / "migrations",
        activate=args.activate,
    )
    report = snapshot_report(snapshot)
    report["version_id"] = version_id
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(run())
