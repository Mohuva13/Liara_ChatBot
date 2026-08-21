import re

from app.ingestion.models import RedactionReport

ENV_SECRET = re.compile(
    r"(?P<prefix>\b(?P<name>[A-Z][A-Z0-9_]*(?:PASSWORD|PASS|TOKEN|SECRET|API_KEY))\s*=\s*[\"']?)"
    r"(?P<value>[^\s\"']+)"
    r"(?P<suffix>[\"']?)"
)
BEARER_SECRET = re.compile(
    r"(?P<prefix>\b(?:Authorization:\s*)?Bearer\s+)(?P<value>[A-Za-z0-9._~-]{12,})",
    re.IGNORECASE,
)
CONNECTION_PASSWORD = re.compile(
    r"(?P<prefix>\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:/@]+:)"
    r"(?P<value>[^\s@/]+)(?P<suffix>@)",
    re.IGNORECASE,
)
EMBEDDED_DATA_URL = re.compile(
    r"(?P<prefix>data:(?:image|audio|video)/[a-z0-9.+-]+;base64,)"
    r"[a-z0-9+/=_-]{1024,}",
    re.IGNORECASE,
)


def redact_credentials(text: str) -> tuple[str, RedactionReport]:
    report = RedactionReport()

    def redact_env(match: re.Match[str]) -> str:
        report.record("environment_value", 1)
        placeholder = f"<YOUR_{match.group('name')}>"
        return f"{match.group('prefix')}{placeholder}{match.group('suffix')}"

    def redact_bearer(match: re.Match[str]) -> str:
        report.record("bearer_token", 1)
        return f"{match.group('prefix')}<YOUR_TOKEN>"

    def redact_connection(match: re.Match[str]) -> str:
        report.record("connection_password", 1)
        return f"{match.group('prefix')}<YOUR_PASSWORD>{match.group('suffix')}"

    redacted = ENV_SECRET.sub(redact_env, text)
    redacted = BEARER_SECRET.sub(redact_bearer, redacted)
    redacted = CONNECTION_PASSWORD.sub(redact_connection, redacted)
    redacted, data_url_count = EMBEDDED_DATA_URL.subn(
        r"\g<prefix><REDACTED_EMBEDDED_ASSET>", redacted
    )
    report.record("embedded_data_url", data_url_count)
    return redacted, report
