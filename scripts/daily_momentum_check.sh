#!/usr/bin/env bash
# After scripts/daily_check.sh, grep momentum / cache-only / mixed cues from today's daily report.
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

echo "=== daily-momentum-check: running daily-check ==="
out="$(bash "${ROOT}/scripts/daily_check.sh" 2>&1)"
printf '%s\n' "${out}"

path="$(printf '%s' "${out}" | sed -n 's/^daily report created: //p' | tail -n 1)"
if [[ -z "${path}" ]] || [[ ! -f "${path}" ]]; then
  echo "daily-momentum-check: ERROR: could not resolve daily report path" >&2
  exit 1
fi

echo ""
echo "=== momentum / cache signals excerpt (${path}) ==="
# Section headers and table hints (no secrets).
grep -nE '## Momentum Signals|Cache Only|Mixed / System Validation|Synthetic fallback|not actionable|\| cache \||\| synthetic \||\*\*Bars source:\*\*|7011|6501|6506|5802' "${path}" || true
echo "=== end excerpt ==="

"${PYTHON}" "${ROOT}/scripts/ops_write_json.py" --mode momentum
