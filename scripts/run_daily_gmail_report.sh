#!/usr/bin/env bash
# Daily operator bundle + Gmail report (dry-run default; gated --send).
set -euo pipefail

usage() {
  echo "Usage: $0 [--dry-run|--send]" >&2
  echo "  --dry-run  Generate bundle + email previews only (default)." >&2
  echo "  --send     Send via Gmail if CONFIRM_GMAIL_SEND=YES and credentials configured." >&2
  exit 2
}

MODE="dry-run"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) MODE="dry-run"; shift ;;
    --send) MODE="send"; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown argument: $1" >&2; usage ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    PYTHON="${ROOT}/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

DAILY_GMAIL_ENV="${HOME}/.config/invest-alpha-os/daily_gmail.env"
if [[ -f "${DAILY_GMAIL_ENV}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${DAILY_GMAIL_ENV}"
  set +a
fi

RUN_DATE="$("${PYTHON}" -c "from invis_alpha_os.utils.date_utils import today_jst_iso; print(today_jst_iso())")"
BUNDLE_DIR="${ROOT}/outputs/operator/daily_usage/${RUN_DATE}"
LOG_FILE="${BUNDLE_DIR}/run_0700.log"
STATUS_FILE="${BUNDLE_DIR}/status.json"
SENT_MARKER="${BUNDLE_DIR}/email_sent.json"

mkdir -p "${BUNDLE_DIR}"
exec >>"${LOG_FILE}" 2>&1
echo "=== run_daily_gmail_report ${RUN_DATE} $(date -u +%Y-%m-%dT%H:%M:%SZ) mode=${MODE} ==="

if ! "${PYTHON}" -m invis_alpha_os.cli.main daily-email --help >/dev/null 2>&1; then
  echo "ERROR: daily-email CLI not found; merge R6.19-A first."
  exit 2
fi

if [[ -f "${SENT_MARKER}" ]] && [[ "${FORCE_DAILY_GMAIL_SEND:-}" != "YES" ]]; then
  echo "SKIP: ${SENT_MARKER} exists (set FORCE_DAILY_GMAIL_SEND=YES to override)"
  "${PYTHON}" -c "
import json, pathlib
p = pathlib.Path('${STATUS_FILE}')
p.write_text(json.dumps({'date':'${RUN_DATE}','status':'skipped_duplicate','mode':'${MODE}'}, indent=2), encoding='utf-8')
"
  exit 0
fi

# Bundle generation (read-only; no market cache write)
export JQUANTS_API_KEY= JQUANTS_ENABLED= JQUANTS_ALLOW_LIVE_HTTP= JQUANTS_API_BASE_URL=

echo "--- daily --us-cache-preview ---"
daily_out="$("${PYTHON}" -m invis_alpha_os.cli.main daily --us-cache-preview 2>&1)" || true
printf '%s\n' "${daily_out}"
daily_path="$(printf '%s' "${daily_out}" | sed -n 's/^daily report created: //p' | tail -n 1)"
if [[ -n "${daily_path}" && -f "${daily_path}" ]]; then
  cp "${daily_path}" "${BUNDLE_DIR}/daily_us_cache_preview.md"
else
  echo "WARN: daily report path missing"
fi

echo "--- signals --dry-run --us-cache-preview --format markdown ---"
"${PYTHON}" -m invis_alpha_os.cli.main signals --dry-run --us-cache-preview --format markdown \
  > "${BUNDLE_DIR}/signals_us_cache_preview.md" 2>&1 || true

MAIN_SHA="$(git -C "${ROOT}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
cat > "${BUNDLE_DIR}/operator_summary.md" <<EOF
# Daily Operator Summary

## Date / Commit
- date: ${RUN_DATE}
- main: \`${MAIN_SHA}\`
- generated at: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Available Outputs
- daily US cache preview: \`${BUNDLE_DIR}/daily_us_cache_preview.md\`
- signals US cache preview: \`${BUNDLE_DIR}/signals_us_cache_preview.md\`

## Safety Checks
| item | result |
|---|---|
| bundle generated | pass |
| mode | ${MODE} |

## How to Use
Observation material only — not buy/sell advice.
EOF

if [[ "${MODE}" == "dry-run" ]]; then
  echo "--- daily-email --dry-run ---"
  "${PYTHON}" -m invis_alpha_os.cli.main daily-email --bundle-dir "${BUNDLE_DIR}" --dry-run --main-commit "${MAIN_SHA}"
  "${PYTHON}" -c "
import json, pathlib, datetime
p = pathlib.Path('${STATUS_FILE}')
p.write_text(json.dumps({
  'date': '${RUN_DATE}',
  'status': 'dry_run_ok',
  'mode': 'dry-run',
  'bundle_dir': '${BUNDLE_DIR}',
  'completed_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
}, indent=2), encoding='utf-8')
"
  echo "OK: dry-run complete"
  exit 0
fi

echo "--- daily-email --send (gated) ---"
if [[ "${CONFIRM_GMAIL_SEND:-}" != "YES" ]]; then
  echo "ERROR: CONFIRM_GMAIL_SEND=YES required for --send"
  exit 2
fi
if [[ -z "${GMAIL_REPORT_TO:-}" ]]; then
  echo "ERROR: GMAIL_REPORT_TO required for --send"
  exit 2
fi

if "${PYTHON}" -m invis_alpha_os.cli.main daily-email --bundle-dir "${BUNDLE_DIR}" --send --main-commit "${MAIN_SHA}"; then
  "${PYTHON}" -c "
import json, pathlib, datetime
sent = pathlib.Path('${SENT_MARKER}')
status = pathlib.Path('${STATUS_FILE}')
sent.write_text(json.dumps({'date':'${RUN_DATE}','sent_at':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}, indent=2), encoding='utf-8')
status.write_text(json.dumps({
  'date': '${RUN_DATE}',
  'status': 'sent_ok',
  'mode': 'send',
  'bundle_dir': '${BUNDLE_DIR}',
  'completed_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
}, indent=2), encoding='utf-8')
"
  echo "OK: send complete"
  exit 0
fi

echo "ERROR: daily-email --send failed"
exit 1
