#!/usr/bin/env bash
# Laputa Alpha OS — Codex CLI review → latest.md（人間向け）+ latest.json（機械門番）
# Does not: git add/commit/push, source .env, pass credentials into the prompt.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p .ai/reviews

OUT_MD="${ROOT}/.ai/reviews/latest.md"
OUT_JSON="${ROOT}/.ai/reviews/latest.json"
STAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

_pick_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    printf '%s' "${PYTHON}"
  elif [[ -x "${ROOT}/.venv/bin/python" ]]; then
    printf '%s' "${ROOT}/.venv/bin/python"
  else
    printf '%s' "python3"
  fi
}
PY="$(_pick_python)"

_write_skipped_json() {
  "${PY}" - "${OUT_JSON}" <<'SKIPPY'
import json
import sys
from pathlib import Path

rec = {
    "schema_version": 1,
    "review_run_status": "skipped",
    "critical": [],
    "important": [],
    "minor": [],
    "recommended_fixes": [],
    "decision": "pass",
}
Path(sys.argv[1]).write_text(
    json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
SKIPPY
}

_write_failed_json() {
  "${PY}" - "${OUT_JSON}" <<'FAILPY'
import json
import sys
from pathlib import Path

rec = {
    "schema_version": 1,
    "review_run_status": "failed",
    "critical": ["codex_cli_exited_nonzero"],
    "important": [],
    "minor": [],
    "recommended_fixes": [],
    "decision": "fail",
}
Path(sys.argv[1]).write_text(
    json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
FAILPY
}

if ! command -v codex >/dev/null 2>&1; then
  {
    echo "# Codex review（スキップ — CLI 未インストール）"
    echo
    echo "Generated: ${STAMP}"
    echo
    echo "この環境では \`codex\` コマンドが PATH 上に見つかりませんでした。"
    echo
    echo "- インストール手順の目安: [Codex CLI](https://developers.openai.com/codex/cli)"
    echo "- 非対話モードは \`codex exec\`（本スクリプトで利用）です。"
    echo
    echo "CLI を入れたあと \`make codex-review\` を再実行すると、ここへレビュー本文が保存されます。"
  } >"${OUT_MD}"
  _write_skipped_json
  echo "codex-review: Codex CLI が見つからないためスキップしました。説明は ${OUT_MD} 、機械状態は ${OUT_JSON} （review_run_status=skipped）を参照してください。" >&2
  exit 0
fi

GS="$(git -C "${ROOT}" status --short 2>&1 || true)"
GDS="$(git -C "${ROOT}" diff --stat 2>&1 || true)"

{
  echo "# Codex review"
  echo
  echo "Generated: ${STAMP}"
  echo "Workspace: ${ROOT}"
  echo
  echo "## Local git context（**.env は読み込まず、credentials もプロンプトに含めません**）"
  echo
  echo '```text'
  echo "${GS}"
  echo
  echo "${GDS}"
  echo '```'
  echo
  echo "## Codex output"
  echo
} >"${OUT_MD}"

# Codex CLI v0.130+: sandbox / ask-for-approval before exec; ephemeral & -C on exec.
set +e
{
  cat <<'P1'
You are a senior reviewer for the Laputa Alpha OS (invest-alpha-os) repository.

STRICT RULES FOR THIS RUN:
- Read-only review: respond primarily in markdown prose for humans. Additionally you MUST output exactly one automation block described below using line markers (exact whole lines — do NOT mention those marker lines inside other sentences).
- Do NOT read, open, or ask anyone to open: .env, .env.* (except .env.example), credentials.json, token.json, secrets/, keys/, or real data under outputs/.
- Do not run or suggest running live trading, external paid APIs with real keys, or curl/fetch against private endpoints for verification.
- Base conclusions on safe repo areas (src, tests, docs, .github, Makefile, config templates) and the git context block below.

CONTEXT — git status --short and git diff --stat only:

P1
  printf '%s\n\n%s\n' "${GS}" "${GDS}"
  cat <<'P2'

Review focus (Critical / Important / Minor where helpful):
1. Phase scope: changes must not exceed the intended phase.
2. No secrets: .env, credentials, tokens, real outputs data must not be committed or pasted into docs.
3. GitHub Actions / CI breakage risk.
4. make verify consistency.
5. Live API unexpected execution.
6. Logging/CLI: no tokens or raw auth in logs.
7. Separation: config vs docs vs src.

End with markdown summary then, on NEW LINES ONLY, the gate block:

First line MUST be exactly (no spaces before/after):
CODEX_REVIEW_JSON_START

Next lines: ONE JSON object ONLY (compact or pretty, no markdown fences), with ALL of these keys:
- "schema_version": integer 1
- "review_run_status": string "executed"
- "critical", "important", "minor", "recommended_fixes": JSON arrays. Each element MUST be a JSON string ONLY (no null, numbers, booleans, objects, or nested arrays). Empty strings and whitespace-only strings are forbidden — omit the entry instead of using "".
- "decision": one of "pass" | "fail" | "needs_human_review" (no other values)

RULES tying severity to decision:
1. Any Critical finding → list in "critical" AND set decision to "fail".
2. Zero Critical BUT any Important finding → list in "important" AND set decision to "needs_human_review".
3. If both critical and important arrays are EMPTY → decision MUST be "pass".
4. If "critical" is non-empty decision MUST NOT be pass or needs_human_review.
5. If "important" is non-empty decision MUST NOT be pass.
6. Valid JSON only: ASCII keys, double quotes, NO trailing commas.
7. Do NOT duplicate line markers elsewhere in prose (explain in words if needed).

Last line MUST be exactly:
CODEX_REVIEW_JSON_END

P2
} | codex --sandbox read-only --ask-for-approval never exec --ephemeral -C "${ROOT}" - >>"${OUT_MD}"
CODEX_RC=$?
set -e

if [[ "${CODEX_RC}" -ne 0 ]]; then
  {
    echo
    echo "---"
    echo "*Codex が終了コード ${CODEX_RC} で終了しました（詳細はターミナル stderr を参照）。*"
  } >>"${OUT_MD}"
  _write_failed_json
  echo "codex-review: Codex が非ゼロ終了しました。${OUT_JSON} に review_run_status=failed を記録しました。" >&2
  exit "${CODEX_RC}"
fi

set +e
"${PY}" - "${OUT_MD}" "${OUT_JSON}" <<'EXTRACTPY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MARK_START = "CODEX_REVIEW_JSON_START"
MARK_END = "CODEX_REVIEW_JSON_END"


def fence_strip(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        # ```json?\n...\n```
        nl = t.find("\n")
        if nl != -1:
            t = t[nl + 1 :].rsplit("```", 1)[0].strip()
    return t


def collect_blocks_exact_lines(content: str) -> list[str]:
    lines = content.splitlines()
    blocks: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if lines[i] != MARK_START:
            i += 1
            continue
        j = i + 1
        while j < n and lines[j] != MARK_END:
            j += 1
        if j < n and lines[j] == MARK_END:
            blob = "\n".join(lines[i + 1 : j]).strip()
            if blob:
                blocks.append(blob)
            i = j + 1
        else:
            i += 1
    return blocks


def elems_ok(arr: object, *, allow_nonempty_only: bool) -> bool:
    if not isinstance(arr, list):
        return False
    for x in arr:
        if not isinstance(x, str):
            return False
        if allow_nonempty_only and not x.strip():
            return False
    return True


def strict_strip_string_array(raw: dict, key: str) -> list[str] | None:
    """Validated list of stripped non-empty strings, or None on any violation (no dropping bad items)."""
    arr = raw.get(key)
    if not isinstance(arr, list):
        return None
    out: list[str] = []
    for item in arr:
        if type(item) is not str:
            return None
        s = item.strip()
        if not s:
            return None
        out.append(s)
    return out


def validate_normalized(data: dict) -> tuple[bool, str]:
    """Return (ok, err)."""
    if data.get("schema_version") != 1:
        return False, 'schema_version must be integer 1'
    rs = data.get("review_run_status")
    if rs != "executed":
        return False, 'review_run_status inside gate JSON must be "executed"'
    critical = data.get("critical") or []
    important = data.get("important") or []
    minor = data.get("minor") or []
    fixes = data.get("recommended_fixes") or []

    if not elems_ok(critical, allow_nonempty_only=True):
        return False, "critical must be a list of non-empty strings"
    if not elems_ok(important, allow_nonempty_only=True):
        return False, "important must be a list of non-empty strings"
    if not elems_ok(minor, allow_nonempty_only=True):
        return False, "minor must be a list of non-empty strings"
    if not elems_ok(fixes, allow_nonempty_only=True):
        return False, "recommended_fixes must be a list of non-empty strings"

    d = data.get("decision")
    if not isinstance(d, str) or d.strip() != d:
        return False, "invalid decision"
    if d not in {"pass", "fail", "needs_human_review"}:
        return False, f'decision must be pass|fail|needs_human_review, got {d!r}'
    crit_n = len(critical)
    imp_n = len(important)
    if crit_n > 0 and d != "fail":
        return False, "critical non-empty requires decision fail"
    if imp_n > 0 and crit_n == 0 and d != "needs_human_review":
        return False, "important non-empty with no critical requires needs_human_review"
    if crit_n == 0 and imp_n == 0 and d != "pass":
        return False, "empty critical and important requires decision pass"
    if d == "needs_human_review" and imp_n == 0:
        return False, "needs_human_review requires non-empty important"
    if d == "pass" and (crit_n > 0 or imp_n > 0):
        return False, "pass requires empty critical and important"
    return True, ""


REQUIRED_GATE_KEYS = frozenset({
    "schema_version",
    "review_run_status",
    "critical",
    "important",
    "minor",
    "recommended_fixes",
    "decision",
})


def try_block(blob: str) -> dict | None:
    blob = fence_strip(blob)
    if not blob or not blob.lstrip().startswith("{"):
        m = re.search(r"\{[\s\S]*\}\s*", blob)
        if not m:
            return None
        blob = m.group(0).strip()

    try:
        raw = json.loads(blob)
    except json.JSONDecodeError:
        return None

    if not isinstance(raw, dict):
        return None
    if not REQUIRED_GATE_KEYS.issubset(raw.keys()):
        return None
    if raw.get("schema_version") != 1:
        return None
    if raw.get("review_run_status") != "executed":
        return None

    list_keys = ("critical", "important", "minor", "recommended_fixes")
    parts: dict[str, list[str]] = {}
    for k in list_keys:
        stripped = strict_strip_string_array(raw, k)
        if stripped is None:
            return None
        parts[k] = stripped

    if not isinstance(raw["decision"], str):
        return None
    decision = raw["decision"].strip()

    normalized = {
        "schema_version": 1,
        "review_run_status": "executed",
        "critical": parts["critical"],
        "important": parts["important"],
        "minor": parts["minor"],
        "recommended_fixes": parts["recommended_fixes"],
        "decision": decision,
    }

    ok, _ = validate_normalized(normalized)
    return normalized if ok else None


def main() -> None:
    md_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    md_text = md_path.read_text(encoding="utf-8", errors="replace")
    blobs = collect_blocks_exact_lines(md_text)
    chosen = None

    # Last successful block wins (iteration from end).
    for blob in reversed(blobs):
        got = try_block(blob)
        if got is not None:
            chosen = got
            break

    if chosen is None:
        fail = {
            "schema_version": 1,
            "review_run_status": "failed",
            "critical": ["codex_review_json_schema_validation_failed"],
            "important": [],
            "minor": [],
            "recommended_fixes": [],
            "decision": "fail",
        }
        out_path.write_text(json.dumps(fail, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            'codex-review: Valid CODEX_REVIEW_JSON block not found after exact-line markers.'
            ' See latest.md.',
            file=sys.stderr,
        )
        sys.exit(1)

    out_path.write_text(
        json.dumps(chosen, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    sys.exit(0)


main()
EXTRACTPY
EXTRACT_RC=$?
set -e

if [[ "${EXTRACT_RC}" -ne 0 ]]; then
  echo "codex-review: Markdown から機械 JSON を検証できませんでした (${OUT_JSON} は failed を記録)。修正して再実行してください。" >&2
  exit 1
fi

echo "codex-review: ${OUT_MD} と ${OUT_JSON} を更新しました。"
exit 0
