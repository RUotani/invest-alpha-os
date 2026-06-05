#!/usr/bin/env bash
# Weekly Candidate Brief generator for launchd (Saturday 07:00 JST).
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

REPORT_DATE="$("${PYTHON}" -c "from invis_alpha_os.utils.date_utils import today_jst_iso; print(today_jst_iso())")"
REPORT_DIR="${ROOT}/reports/${REPORT_DATE}"
LOG_DIR="${ROOT}/outputs/operator/weekly_candidate_brief/${REPORT_DATE}"
LOG_FILE="${LOG_DIR}/run_0700.log"
STATUS_FILE="${LOG_DIR}/status.json"
FULL_MD="${REPORT_DIR}/weekly_candidate_brief_v0_1.md"
COPY_MD="${REPORT_DIR}/weekly_candidate_brief_copy.md"
JSON_FILE="${REPORT_DIR}/weekly_candidate_brief.json"
EMAIL_TXT="${REPORT_DIR}/email/email_preview.txt"
EMAIL_HTML="${REPORT_DIR}/email/email_preview.html"
EMAIL_EML="${REPORT_DIR}/email/email_preview.eml"

mkdir -p "${REPORT_DIR}" "${LOG_DIR}"
exec >>"${LOG_FILE}" 2>&1
echo "=== run_weekly_candidate_brief ${REPORT_DATE} $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# Safety baseline: keep observation-only mode and avoid live HTTP toggles.
export JQUANTS_API_KEY= JQUANTS_ENABLED= JQUANTS_ALLOW_LIVE_HTTP= JQUANTS_API_BASE_URL=
export CONFIRM_US_LIVE_HTTP=

"${PYTHON}" -m invis_alpha_os.cli.main weekly-candidate-brief \
  --format markdown \
  --report-date "${REPORT_DATE}" \
  --out "${FULL_MD}"

"${PYTHON}" -m invis_alpha_os.cli.main weekly-candidate-brief \
  --format copy \
  --report-date "${REPORT_DATE}" \
  --out "${COPY_MD}"

"${PYTHON}" -m invis_alpha_os.cli.main weekly-candidate-brief \
  --format json \
  --report-date "${REPORT_DATE}" \
  --out "${JSON_FILE}"

"${PYTHON}" -m invis_alpha_os.cli.main weekly-candidate-brief-email \
  --report-date "${REPORT_DATE}" \
  --report-dir "${REPORT_DIR}" \
  --copy-file "${COPY_MD}" \
  --full-md "${FULL_MD}"

"${PYTHON}" -m invis_alpha_os.product.weekly_artifact_status_schema_v104 \
  --status-file "${STATUS_FILE}" \
  --report-date "${REPORT_DATE}" \
  --full-report "${FULL_MD}" \
  --copy-report "${COPY_MD}" \
  --json-report "${JSON_FILE}" \
  --email-text "${EMAIL_TXT}" \
  --email-html "${EMAIL_HTML}" \
  --email-eml "${EMAIL_EML}"

if [[ -f "${HOME}/.config/invest-alpha-os/weekly_report_email.env" ]]; then
  # shellcheck source=/dev/null
  set -a && source "${HOME}/.config/invest-alpha-os/weekly_report_email.env" && set +a
elif [[ -f "${HOME}/.config/invest-alpha-os/daily_gmail.env" ]]; then
  # shellcheck source=/dev/null
  set -a && source "${HOME}/.config/invest-alpha-os/daily_gmail.env" && set +a
fi
export WEEKLY_REPORT_EMAIL_ENABLED="${WEEKLY_REPORT_EMAIL_ENABLED:-true}"

echo "=== weekly-report-email-send ${REPORT_DATE} ==="
if ! "${PYTHON}" -m invis_alpha_os.cli.main weekly-report-email-send \
  --report-date "${REPORT_DATE}" \
  --report-root "${REPORT_DIR}" \
  --send \
  --no-auto-env-file \
  --format markdown; then
  echo "WARN: weekly report email send failed (artifacts remain in ${REPORT_DIR})"
fi

echo "OK: weekly candidate brief generated"
