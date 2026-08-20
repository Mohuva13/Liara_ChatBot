"""Safe interactive smoke test for an OpenAI-compatible provider.

The key is read from an environment variable or a hidden terminal prompt. It is
never accepted as a command-line argument and is never printed.
"""

import asyncio
import getpass
import os
import sys
import uuid

import httpx


def secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    if not sys.stdin.isatty():
        raise SystemExit(f"{name} is required in a non-interactive session")
    value = getpass.getpass(f"{name} (hidden): ").strip()
    if not value:
        raise SystemExit(f"{name} cannot be empty")
    return value


async def main() -> None:
    base_url = os.getenv("LLM_BASE_URL", "https://api.avalai.ir/v1").rstrip("/")
    embedding_base_url = os.getenv("EMBEDDING_BASE_URL", base_url).rstrip("/")
    llm_key = secret("LLM_API_KEY")
    embedding_key = os.getenv("EMBEDDING_API_KEY", "").strip() or llm_key
    llm_model = os.getenv("LLM_SMALL_MODEL", "").strip()
    embedding_model = os.getenv("EMBEDDING_MODEL", "").strip()
    if not llm_model or not embedding_model:
        raise SystemExit("LLM_SMALL_MODEL and EMBEDDING_MODEL are required")

    timeout = httpx.Timeout(60)
    request_id = uuid.uuid4().hex
    async with httpx.AsyncClient(timeout=timeout) as client:
        completion = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "authorization": f"Bearer {llm_key}",
                "x-request-id": request_id,
            },
            json={
                "model": llm_model,
                "messages": [
                    {
                        "role": "user",
                        "content": 'Only return this JSON: {"status":"ok"}',
                    }
                ],
                "max_tokens": 30,
                "response_format": {"type": "json_object"},
            },
        )
        completion.raise_for_status()
        completion_body = completion.json()
        if not completion_body.get("choices"):
            raise SystemExit("completion response has no choices")

        embedding = await client.post(
            f"{embedding_base_url}/embeddings",
            headers={
                "authorization": f"Bearer {embedding_key}",
                "x-request-id": uuid.uuid4().hex,
            },
            json={"model": embedding_model, "input": ["مستندات لیارا"]},
        )
        embedding.raise_for_status()
        vector = embedding.json()["data"][0]["embedding"]
        if not isinstance(vector, list) or not vector:
            raise SystemExit("embedding response is empty")

    print(f"provider smoke passed; embedding_dimensions={len(vector)}")


if __name__ == "__main__":
    asyncio.run(main())
