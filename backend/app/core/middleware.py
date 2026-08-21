import json
import secrets
import time

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import telemetry_event
from app.core.metrics import metrics


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") in {"GET", "HEAD"}:
            await self._app(scope, receive, send)
            return

        declared_length = next(
            (
                value
                for name, value in scope.get("headers", [])
                if name.lower() == b"content-length"
            ),
            None,
        )
        if declared_length is not None:
            try:
                if int(declared_length) > self._max_bytes:
                    await self._reject(scope, send)
                    return
            except ValueError:
                await self._reject(scope, send)
                return

        chunks: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > self._max_bytes:
                await self._reject(scope, send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        delivered = False

        async def replay_receive() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": b"".join(chunks)}

        await self._app(scope, replay_receive, send)

    @staticmethod
    async def _reject(scope: Scope, send: Send) -> None:
        request_id = scope.get("state", {}).get("request_id", "unknown")
        body = json.dumps(
            {
                "error": {
                    "code": "request_too_large",
                    "message": "حجم درخواست بیش از حد مجاز است.",
                    "request_id": request_id,
                    "details": None,
                }
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode()),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id = secrets.token_hex(16)
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                headers["X-Frame-Options"] = "DENY"
                headers["Permissions-Policy"] = (
                    "camera=(), microphone=(), geolocation=()"
                )
                headers["Content-Security-Policy"] = (
                    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
                )
            await send(message)

        try:
            await self._app(scope, receive, send_with_headers)
        finally:
            route = getattr(scope.get("route"), "path", "unmatched")
            telemetry_event(
                "http_request",
                request_id=request_id,
                method=scope.get("method", "unknown"),
                route=route,
                status_code=status_code,
                latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
                outcome="success" if status_code < 400 else "error",
            )
            metrics.increment(
                "liara_http_requests_total",
                method=str(scope.get("method", "unknown")),
                route=str(route),
                status=str(status_code),
            )
            metrics.increment(
                "liara_http_latency_milliseconds_total",
                (time.perf_counter() - started_at) * 1000,
                route=str(route),
            )


class InternalAuthMiddleware:
    def __init__(self, app: ASGIApp, *, token: str | None) -> None:
        self._app = app
        self._token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = str(scope.get("path", ""))
        if scope["type"] != "http" or not path.startswith("/v1/"):
            await self._app(scope, receive, send)
            return
        if self._token is None:
            await self._app(scope, receive, send)
            return
        supplied = next(
            (
                value.decode(errors="ignore")
                for name, value in scope.get("headers", [])
                if name.lower() == b"x-internal-token"
            ),
            "",
        )
        if secrets.compare_digest(supplied, self._token):
            await self._app(scope, receive, send)
            return
        body = b'{"error":{"code":"internal_auth_failed","message":"Unauthorized"}}'
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
