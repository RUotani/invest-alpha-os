#!/usr/bin/env bash
# Run `daily` (no live HTTP), print J-Quants Watchlist Bars Check section, leak-grep excerpt.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    PYTHON="${ROOT}/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

echo "=== daily-check (PYTHON=${PYTHON}) ==="

out="$("${PYTHON}" -m invis_alpha_os.cli.main daily 2>&1)"
printf '%s\n' "${out}"

path="$(printf '%s' "${out}" | sed -n 's/^daily report created: //p' | tail -n 1)"
if [[ -z "${path}" ]] || [[ ! -f "${path}" ]]; then
  echo "daily-check: ERROR: could not resolve daily report path from CLI output" >&2
  exit 1
fi

echo ""
echo "--- excerpt: ## J-Quants Watchlist Bars Check ---"
section=""
# shellcheck disable=SC2016
section="$(awk '
  /^## J-Quants Watchlist Bars Check$/ { p = 1; print; next }
  p && /^## / && $0 != "## J-Quants Watchlist Bars Check" { exit }
  p { print }
' "${path}")" || true

if [[ -z "${section}" ]]; then
  echo "daily-check: ERROR: section not found in ${path}" >&2
  exit 1
fi

printf '%s\n' "${section}"
echo "--- end excerpt ---"

leak_fail() {
  echo "daily-check: ERROR: excerpt failed leak heuristics ($1)" >&2
  exit 1
}

# Heuristics only — rejects likely secret material, not the words "x-api-key" in prose.
if printf '%s' "${section}" | grep -qEi 'x-api-key[[:space:]]*:[[:space:]]*[A-Za-z0-9_-]{16,}'; then
  leak_fail "possible x-api-key value"
fi
if printf '%s' "${section}" | grep -qEi 'Authorization:[[:space:]]*Bearer[[:space:]]+[A-Za-z0-9._-]{16,}'; then
  leak_fail "possible bearer token"
fi
if printf '%s' "${section}" | grep -qE 'JQUANTS_API_KEY[[:space:]]*=[[:space:]]*[^[:space:]#"'\'']+[[:space:]]*$'; then
  leak_fail "possible env assignment of JQUANTS_API_KEY"
fi
if printf '%s' "${section}" | grep -qE '"raw_response"[[:space:]]*:[[:space:]]*"[^"]{80}'; then
  leak_fail 'possible embedded raw_response string blob'
fi

echo ""
echo "daily-check: excerpt leak heuristics: OK"
echo "=== end daily-check ==="
