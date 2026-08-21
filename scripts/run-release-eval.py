"""Run the versioned release evaluation against a real deployed backend."""

import asyncio
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals" / "datasets" / "golden.jsonl"


def headers() -> dict[str, str]:
    token = os.getenv("API_INTERNAL_TOKEN", "").strip()
    return {"x-internal-token": token} if token else {}


def parse_sse(body: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in body.split("\n\n"):
        data = next(
            (line[6:] for line in block.splitlines() if line.startswith("data: ")),
            None,
        )
        if data:
            events.append(json.loads(data))
    return events


async def evaluate(client: httpx.AsyncClient, row: dict[str, Any]) -> dict[str, Any]:
    session_response = await client.post("/v1/sessions", headers=headers())
    session_response.raise_for_status()
    session_id = session_response.json()["session_id"]
    started = time.perf_counter()
    response = await client.post(
        "/v1/chat/stream",
        headers={**headers(), "content-type": "application/json"},
        json={
            "protocol_version": "1",
            "session_id": session_id,
            "message_id": f"eval-{row['id']}",
            "text": row["query"],
            "surface": "page",
            "locale": "fa-IR",
        },
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    response.raise_for_status()
    events = parse_sse(response.text)
    end = next((event for event in events if event["type"] == "message_end"), {})
    outcome = end.get("outcome", "missing")
    sources = next(
        (event.get("sources", []) for event in events if event["type"] == "sources"),
        [],
    )
    urls = [source["url"] for source in sources]
    expected = row["expected_urls"]
    expected_in_scope = row["expected_in_scope"]
    if not expected_in_scope:
        passed = outcome == "out_of_scope" and not urls
    elif expected:
        passed = outcome == "answered" and all(url in urls for url in expected)
    else:
        passed = outcome in {"clarification", "support", "answered"}
    rank = min((urls.index(url) + 1 for url in expected if url in urls), default=0)
    return {
        "id": row["id"],
        "passed": passed,
        "outcome": outcome,
        "expected_urls": expected,
        "returned_urls": urls,
        "reciprocal_rank": (1 / rank) if rank else 0,
        "latency_ms": latency_ms,
    }


async def main() -> int:
    base_url = os.getenv("EVAL_BASE_URL", "http://localhost:8000").rstrip("/")
    rows = [json.loads(line) for line in DATASET.read_text().splitlines() if line]
    async with httpx.AsyncClient(base_url=base_url, timeout=90) as client:
        results = [await evaluate(client, row) for row in rows]
    url_cases = [result for result in results if result["expected_urls"]]
    latencies = sorted(float(result["latency_ms"]) for result in results)
    p95_index = max(0, min(len(latencies) - 1, int(len(latencies) * 0.95) - 1))
    report = {
        "dataset": str(DATASET.relative_to(ROOT)),
        "cases": len(results),
        "pass_rate": sum(result["passed"] for result in results) / len(results),
        "expected_source_recall": (
            sum(result["passed"] for result in url_cases) / len(url_cases)
            if url_cases
            else 1
        ),
        "mrr": (
            statistics.fmean(result["reciprocal_rank"] for result in url_cases)
            if url_cases
            else 1
        ),
        "p95_latency_ms": latencies[p95_index],
        "results": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    passed = (
        report["pass_rate"] >= 0.9
        and report["expected_source_recall"] >= 0.9
        and report["mrr"] >= 0.75
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
