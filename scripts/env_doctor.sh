#!/usr/bin/env bash
# Show J-Quants-related env *presence* only (never values or full .env).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "=== env-doctor ==="
echo "repo: ${ROOT}"
if [[ -f "${ROOT}/.env" ]]; then
  echo ".env file: present (contents not displayed)"
else
  echo ".env file: absent"
fi
echo "---"

vars_boolish=(
  JQUANTS_ENABLED
  JQUANTS_ALLOW_LIVE_HTTP
)

vars_plain=(
  JQUANTS_API_VERSION
  JQUANTS_API_BASE_URL
  JQUANTS_API_KEY
  JQUANTS_DATA_AVAILABLE_FROM
  JQUANTS_DATA_AVAILABLE_TO
)

if [[ -f "${ROOT}/.env" ]]; then
  # shellcheck disable=SC1090,SC1091
  set -a
  # Do not emit .env to stdout/stderr here.
  source "${ROOT}/.env"
  set +a
fi

describe_boolish() {
  local name="$1"
  # Bash 3.2–compatible indirect read (avoid [[ -v ]])
  # shellcheck disable=SC2163
  if [[ -z ${!name+x} ]] || [[ -z "${!name}" ]]; then
    printf '%s: missing\n' "${name}"
    return 0
  fi
  local v raw
  raw="${!name}"
  v="$(printf '%s' "${raw}" | tr '[:upper:]' '[:lower:]')"
  case "${v}" in
    true|1|yes) printf '%s: true\n' "${name}" ;;
    false|0|no) printf '%s: false\n' "${name}" ;;
    *) printf '%s: present (non-boolean literal; value hidden)\n' "${name}" ;;
  esac
}

describe_plain() {
  local name="$1"
  # shellcheck disable=SC2163
  if [[ -z ${!name+x} ]] || [[ -z "${!name}" ]]; then
    printf '%s: missing\n' "${name}"
  else
    printf '%s: present (value hidden)\n' "${name}"
  fi
}

for v in "${vars_boolish[@]}"; do
  describe_boolish "${v}"
done
for v in "${vars_plain[@]}"; do
  describe_plain "${v}"
done

echo "=== end env-doctor ==="
