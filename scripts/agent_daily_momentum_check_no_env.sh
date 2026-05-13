#!/usr/bin/env bash
# Agent-facing variant of scripts/daily_momentum_check.sh: runs ``daily`` with the current process
# environment only (never reads ROOT/.env via load_jquants_env). Mirrors excerpt / ops-write steps.
#
# Humans should keep using ``make daily-momentum-check`` when .env-whitelisted merges are desired.
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

echo "=== agent daily-momentum-check (no .env merge; inherits process env) ==="
set +e
out="$("${PYTHON}" -m invis_alpha_os.cli.main daily 2>&1)"
dm_ec=$?
set -e
printf '%s\n' "${out}"
if [[ "${dm_ec}" != 0 ]]; then
  exit "${dm_ec}"
fi

path="$(printf '%s' "${out}" | sed -n 's/^daily report created: //p' | tail -n 1)"
if [[ -z "${path}" ]] || [[ ! -f "${path}" ]]; then
  echo "agent-daily-momentum: ERROR: could not resolve daily report path" >&2
  exit 1
fi

echo ""
echo "=== momentum / cache signals excerpt (${path}) ==="
grep -nE '## Momentum Signals|Cache Only|Mixed / System Validation|Synthetic fallback|not actionable|\| cache \||\| synthetic \||\*\*Bars source:\*\*|7011|6501|6506|5802' "${path}" || true
echo "=== end excerpt ==="

"${PYTHON}" "${ROOT}/scripts/ops_write_json.py" --mode momentum
