#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
PROJECT_DIR="$(cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd)"

command -v docker >/dev/null || {
  echo "خطا: Docker نصب نیست یا در PATH قرار ندارد." >&2
  exit 1
}
docker info >/dev/null 2>&1 || {
  echo "Docker daemon در دسترس نیست یا کاربر اجازهٔ اتصال ندارد." >&2
  echo "راه سریع: sudo $SCRIPT_PATH" >&2
  echo "راه پایدار: کاربر را به گروه docker اضافه و یک‌بار logout/login کنید." >&2
  exit 1
}

cd "$PROJECT_DIR"
docker compose down --remove-orphans
echo "سرویس‌ها و شبکه متوقف شدند؛ volumeهای PostgreSQL و Redis حفظ شدند."
