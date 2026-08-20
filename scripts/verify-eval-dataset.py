import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.policies.scope import classify_scope  # noqa: E402


def canonical_urls() -> set[str]:
    docs_root = Path("/home/mohuva/Desktop/hackaton/docs/public/llms")
    urls: set[str] = set()
    for path in docs_root.rglob("*.md"):
        first = path.read_text(encoding="utf-8-sig").splitlines()[:1]
        if first and first[0].startswith("Original link: "):
            urls.add(first[0].removeprefix("Original link: ").strip())
    return urls


def main() -> int:
    dataset = ROOT / "evals" / "datasets" / "golden.jsonl"
    rows = [json.loads(line) for line in dataset.read_text().splitlines() if line]
    corpus_urls = canonical_urls()
    missing = sorted(
        url for row in rows for url in row["expected_urls"] if url not in corpus_urls
    )
    correct = sum(
        classify_scope(row["query"]).in_scope == row["expected_in_scope"]
        for row in rows
    )
    accuracy = correct / len(rows)
    report = {
        "cases": len(rows),
        "scope_accuracy": accuracy,
        "missing_expected_urls": missing,
        "passed": accuracy >= 0.9 and not missing,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
