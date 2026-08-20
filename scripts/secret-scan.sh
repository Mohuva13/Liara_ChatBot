#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

if rg -n --hidden \
  --glob '!.git/**' \
  --glob '!*.lock' \
  --glob '!scripts/secret-scan.sh' \
  '(aa-[A-Za-z0-9_-]{30,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)' .
then
  echo "Potential secret found." >&2
  exit 1
fi

echo "Secret scan passed."
