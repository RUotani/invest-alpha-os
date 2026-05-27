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

"${PYTHON}" -c "
import datetime, json, pathlib
status = pathlib.Path('${STATUS_FILE}')
status.write_text(json.dumps({
  'date': '${REPORT_DATE}',
  'status': 'weekly_candidate_brief_generated',
  'full_report': '${FULL_MD}',
  'copy_report': '${COPY_MD}',
  'completed_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
}, indent=2), encoding='utf-8')
"

echo "OK: weekly candidate brief generated"
