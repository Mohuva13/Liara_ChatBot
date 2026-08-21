#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
PROJECT_DIR="$(cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd)"
START_TIMEOUT_SECONDS="${LIARA_START_TIMEOUT_SECONDS:-180}"

diagnostics() {
  local exit_code="$?"
  if ((exit_code == 0)); then
    return
  fi
  echo "شروع سرویس‌ها کامل نشد؛ وضعیت و انتهای لاگ‌ها:" >&2
  docker compose --project-directory "$PROJECT_DIR" ps >&2 || true
  docker compose --project-directory "$PROJECT_DIR" logs --tail=80 >&2 || true
}
wait_for_url() {
  local url="$1"
  local label="$2"
  local elapsed=0

  while ((elapsed < START_TIMEOUT_SECONDS)); do
    if curl --fail --silent --show-error --output /dev/null "$url" 2>/dev/null; then
      echo "✓ $label"
      return 0
    fi
    sleep 2
    ((elapsed += 2))
  done
  echo "خطا: $label پس از ${START_TIMEOUT_SECONDS} ثانیه آماده نشد: $url" >&2
  return 1
}

command -v docker >/dev/null || {
  echo "خطا: Docker نصب نیست یا در PATH قرار ندارد." >&2
  exit 1
}
command -v curl >/dev/null || {
  echo "خطا: curl نصب نیست یا در PATH قرار ندارد." >&2
  exit 1
}
docker info >/dev/null 2>&1 || {
  echo "خطا: Docker daemon در دسترس نیست یا کاربر اجازهٔ اتصال ندارد." >&2
  echo "راه سریع: sudo $SCRIPT_PATH" >&2
  echo "راه پایدار: کاربر را به گروه docker اضافه و یک‌بار logout/login کنید." >&2
  exit 1
}

cd "$PROJECT_DIR"
trap diagnostics EXIT
docker compose config --quiet
echo "ساخت imageها و اجرای سرویس‌های Liara Assistant..."
docker compose up --build --detach --remove-orphans

wait_for_url "http://localhost:8000/health/live" "FastAPI زنده است"

if [[ "${LIARA_RUN_INGESTION:-0}" == "1" ]]; then
  echo "اجرای ingestion افزایشی و فعال‌سازی corpus..."
  docker compose exec -T backend python -m app.ingestion.cli --activate
fi

wait_for_url "http://localhost:8000/health/ready" "FastAPI آماده است"
wait_for_url "http://localhost:3000/chat" "رابط چت آماده است"

docker compose ps
trap - EXIT
echo
echo "Liara Assistant آماده است:"
echo "  Chat:       http://localhost:3000/chat"
echo "  API:        http://localhost:8000"
echo "  Readiness:  http://localhost:8000/health/ready"
