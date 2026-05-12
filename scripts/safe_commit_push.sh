#!/usr/bin/env bash
# Laputa Alpha OS — Safe commit/push automation (gates + forbidden paths + Codex thresholds).
#
# Usage:
#   SAFE_PUSH_MSG="your message" [PYTHON=.venv/bin/python] bash scripts/safe_commit_push.sh
#   DRY_RUN=true SAFE_PUSH_MSG="..." bash scripts/safe_commit_push.sh
#   ALLOW_IMPORTANT=true SAFE_PUSH_MSG="..." bash scripts/safe_commit_push.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PYTHON="${PYTHON:-.venv/bin/python}"
export PYTHON

DRY_RUN="${DRY_RUN:-false}"

die() {
  echo "safe-push: ERROR: $*" >&2
  exit 1
}

warn() {
  echo "safe-push: WARN: $*" >&2
}

usage_safe_push_msg_hint() {
  cat >&2 <<'HINT'
コミットメッセージは環境変数 SAFE_PUSH_MSG で渡してください（Makefile では展開しません）。

例（本番コミット／プッシュフローは人間の明示承認があるときのみ）:
  SAFE_PUSH_MSG="Harden safe push automation workflow" PYTHON=.venv/bin/python make safe-push

dry-run:
  SAFE_PUSH_MSG="Harden safe push automation workflow" PYTHON=.venv/bin/python make safe-push-dry-run
HINT
}

validate_safe_push_msg_or_die() {
  local msg="$1"
  if [[ -z "${msg}" ]]; then
    echo "safe-push: SAFE_PUSH_MSG が空です。非空のコミットメッセージが必要です。" >&2
    usage_safe_push_msg_hint
    exit 1
  fi
  if [[ "${msg}" == *$'\n'* || "${msg}" == *$'\r'* ]]; then
    die "commit message must be a single line (no newlines); use SAFE_PUSH_MSG accordingly"
  fi
  if LC_ALL=C printf '%s' "${msg}" | grep -q '[[:cntrl:]]'; then
    die "commit message must not contain control characters"
  fi
  if ((${#msg} > 120)); then
    die "commit message exceeds 120 characters (length $(( ${#msg} ))); shorten SAFE_PUSH_MSG"
  fi
  if [[ ! "${msg}" =~ ^[-a-zA-Z0-9_./:[:space:]]+$ ]]; then
    die "commit message has disallowed characters (allowed: letters, digits, space, -, _, :, /, .)"
  fi
}

# MSG を一切使わない（Makefile からも渡さない）。設定されているだけで拒否する。
if [[ "${MSG+x}" == x ]]; then
  echo "safe-push: 環境変数 MSG は廃止されました。unset MSG のうえ SAFE_PUSH_MSG を使ってください。" >&2
  usage_safe_push_msg_hint
  exit 1
fi

if [[ -z "${SAFE_PUSH_MSG:-}" ]]; then
  echo "safe-push: SAFE_PUSH_MSG が未設定または空です。" >&2
  usage_safe_push_msg_hint
  exit 1
fi

validate_safe_push_msg_or_die "${SAFE_PUSH_MSG}"

COMMIT_MSG="${SAFE_PUSH_MSG}"

# --- Forbidden path rules (shared: pre / post / staged) ------------------------
# Allowed: .env.example, outputs/**/.gitkeep only (under outputs/).
is_forbidden_path() {
  local p="$1"
  local norm base
  norm="${p#./}"
  base="$(basename "${norm}")"

  [[ "${base}" == ".env" ]] && return 0
  if [[ "${base}" =~ ^\.env\. ]] && [[ "${base}" != ".env.example" ]]; then
    return 0
  fi
  [[ "${base}" == "credentials.json" ]] && return 0
  [[ "${base}" == "token.json" ]] && return 0
  [[ "${norm}" =~ (^|/)secrets/ ]] && return 0
  [[ "${norm}" =~ (^|/)credentials/ ]] && return 0
  [[ "${norm}" =~ (^|/)keys/ ]] && return 0
  if [[ "${norm}" =~ (^|/)\.venv/ ]] || [[ "${norm}" == ".venv" ]]; then
    return 0
  fi
  if [[ "${norm}" =~ (^|/)venv/ ]] || [[ "${norm}" == "venv" ]]; then
    return 0
  fi
  if [[ "${norm}" =~ ^outputs/ ]] && [[ "${base}" != ".gitkeep" ]]; then
    return 0
  fi
  if [[ "${norm}" =~ ^\.ai/reviews/ ]] && ([[ "${norm}" == *.md ]] || [[ "${norm}" == *.json ]]); then
    return 0
  fi
  [[ "${base}" == *.pem ]] && return 0
  [[ "${base}" == *.key ]] && return 0

  return 1
}

# --- Selective staging (Hotfix B: no repository-wide `git add` with -A flag) ----
# Single pass over `git status --short --untracked-files=all` shared by DRY_RUN and commit.

path_is_unsafe_for_add() {
  local p="$1"
  [[ -z "${p}" ]] && return 0
  if LC_ALL=C printf '%s' "${p}" | grep -q '[[:cntrl:]]'; then
    return 0
  fi
  # Leading dash looks like a git option even with `git add --` in some edge cases; refuse.
  [[ "${p}" == -* ]] && return 0
  return 1
}

ensure_index_clean_or_die() {
  local out
  out="$(git -C "${ROOT}" diff --cached --name-only 2>/dev/null || true)"
  if [[ -n "${out}" ]]; then
    {
      echo "pre-staged changes detected. Unstage them first:"
      echo "  git restore --staged <path>"
      echo "or:"
      echo "  git restore --staged ."
      echo ""
      echo "Currently staged:"
      git -C "${ROOT}" diff --cached --name-only | sed 's/^/  /' || true
    } >&2
    exit 1
  fi
}

# Echo sorted unique paths that would be passed to `git add --` (same logic for DRY_RUN and real run).
# Skips ignored paths (`!!`). Dies on conflict XY, rename arrow, or unsafe path.
collect_safe_push_stage_paths_or_die() {
  local line xy rest p
  local -a acc=()
  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ -z "${line}" ]] && continue
    [[ "${line}" == \#\#* ]] && continue
    ((${#line} < 2)) && continue
    xy="${line:0:2}"
    case "${xy}" in
      UU|AA|DD|AU|UA|DU|UD|TT)
        die "conflict detected; resolve before safe-push: ${line}"
        ;;
      !!)
        continue
        ;;
    esac
    ((${#line} < 4)) && continue
    rest="${line:3}"
    [[ -z "${rest}" ]] && continue
    if [[ "${rest}" == *" -> "* ]]; then
      die "rename or copy detected; resolve or commit separately before safe-push (manual: git mv / separate commit). Line: ${line}"
    fi
    p="${rest}"
    if path_is_unsafe_for_add "${p}"; then
      die "unsafe path blocked (empty, control chars, or leading -): ${p}"
    fi
    acc+=("${p}")
  done < <(git -C "${ROOT}" status --short --untracked-files=all)

  if ((${#acc[@]} == 0)); then
    return 0
  fi
  printf '%s\n' "${acc[@]}" | sort -u
  return 0
}

# Collect paths shown by git status -s --untracked-files=all (excluding ## header lines).
gather_paths_from_git_status_short() {
  local line rest
  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ -z "${line}" ]] && continue
    [[ "${line}" == \#\#* ]] && continue
    ((${#line} < 4)) && continue
    rest="${line:3}"
    [[ -z "${rest}" ]] && continue
    if [[ "${rest}" == *" -> "* ]]; then
      printf '%s\n' "${rest%% -> *}"
      printf '%s\n' "${rest#* -> }"
    else
      printf '%s\n' "${rest}"
    fi
  done < <(git -C "${ROOT}" status --short --untracked-files=all)
}

# Args: ctx label — stdin: one path per line (optional leading ./ stripped by is_forbidden).
check_paths_stream_or_die() {
  local ctx="$1"
  local p=
  local -a forbidden_list=()

  while IFS= read -r p || [[ -n "${p}" ]]; do
    [[ -z "${p}" ]] && continue
    if is_forbidden_path "${p}"; then
      forbidden_list+=("${p}")
    fi
  done

  if ((${#forbidden_list[@]} > 0)); then
    local joined
    joined="$(printf '%s; ' "${forbidden_list[@]}")"
    die "forbidden path(s) blocked (${ctx}): ${joined%; }"
  fi
}

# Uses git status --short (--untracked-files=all). Same criterion as stdin check.
check_git_status_paths_or_die() {
  local ctx="$1"
  gather_paths_from_git_status_short | sort -u | check_paths_stream_or_die "${ctx}"
}

analyze_codex_review() {
  local j="${ROOT}/.ai/reviews/latest.json"
  if [[ ! -f "${j}" ]]; then
    die "missing ${j} — run make codex-review（済みでも latest.json が無い場合は安全のため停止）。"
  fi
  set +e
  ALLOW_IMPORTANT_FLAG="${ALLOW_IMPORTANT:-false}"
  "${PYTHON}" - "${j}" "${ALLOW_IMPORTANT_FLAG}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path


def truthy_allow(s: str) -> bool:
    return s.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    path = Path(sys.argv[1])
    allow_important = truthy_allow(sys.argv[2] if len(sys.argv) > 1 else "")

    try:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"safe-push: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(13)

    try:
        data: dict = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"safe-push: latest.json parse error: {e}", file=sys.stderr)
        sys.exit(13)

    rs = data.get("review_run_status")
    if rs != "executed":
        if rs == "failed":
            print(
                "safe-push: latest.json has review_run_status=failed "
                "(Codex/process failure or gate JSON schema validation failed). "
                "commit/push は行いません。ALLOW_IMPORTANT では突破できません。",
                file=sys.stderr,
            )
        elif rs == "skipped":
            print(
                "safe-push: latest.json has review_run_status=skipped (Codex CLI 未導入)。"
                " commit/push は行いません。",
                file=sys.stderr,
            )
        else:
            print(
                f'safe-push: latest.json review_run_status must be "executed" (got {rs!r});'
                " safe-push は実行しません。",
                file=sys.stderr,
            )
        sys.exit(12)

    if data.get("schema_version") != 1:
        print("safe-push: schema_version must be 1", file=sys.stderr)
        sys.exit(14)

    decision = data.get("decision")

    required_list_keys = ("critical", "important", "minor", "recommended_fixes")
    for k in required_list_keys:
        v = data.get(k)
        if not isinstance(v, list):
            print(
                f'safe-push: JSON field "{k}" must be a JSON array (got {type(v).__name__})',
                file=sys.stderr,
            )
            sys.exit(14)

    if not isinstance(decision, str):
        print("safe-push: decision must be a string", file=sys.stderr)
        sys.exit(14)

    decision = decision.strip()

    critical_items: list[str] = []
    for x in data["critical"]:
        if not isinstance(x, str):
            print(
                "safe-push: every item in critical must be a non-empty string",
                file=sys.stderr,
            )
            sys.exit(14)
        sx = x.strip()
        if not sx:
            print(
                "safe-push: empty string in critical[] is not allowed",
                file=sys.stderr,
            )
            sys.exit(14)
        critical_items.append(sx)

    important_items: list[str] = []
    for x in data["important"]:
        if not isinstance(x, str):
            print(
                "safe-push: every item in important must be a non-empty string",
                file=sys.stderr,
            )
            sys.exit(14)
        sx = x.strip()
        if not sx:
            print(
                "safe-push: empty string in important[] is not allowed",
                file=sys.stderr,
            )
            sys.exit(14)
        important_items.append(sx)

    for key in ("minor", "recommended_fixes"):
        for x in data[key]:
            if not isinstance(x, str):
                print(
                    f'safe-push: every item in "{key}" must be a string',
                    file=sys.stderr,
                )
                sys.exit(14)
            if not x.strip():
                print(f'safe-push: empty string in "{key}" is not allowed', file=sys.stderr)
                sys.exit(14)

    if decision not in ("pass", "needs_human_review", "fail"):
        print(f'safe-push: invalid decision "{decision}"', file=sys.stderr)
        sys.exit(14)

    if decision == "needs_human_review" and not important_items:
        print(
            "safe-push: decision needs_human_review requires non-empty important[]",
            file=sys.stderr,
        )
        sys.exit(14)

    force_critical_stop = critical_items or decision == "fail"
    if force_critical_stop:
        sys.exit(10)

    needs_important_review = decision == "needs_human_review" or important_items
    if decision == "pass" and important_items:
        needs_important_review = True

    if needs_important_review:
        if allow_important:
            print(
                "safe-push: ALLOW_IMPORTANT=true — needs_human_review または important が非空。続行します。",
                file=sys.stderr,
            )
        sys.exit(0 if allow_important else 11)

    if decision != "pass":
        sys.exit(14)

    sys.exit(0)


main()
PY
  local rc=$?
  set -e
  case "${rc}" in
    0) return 0 ;;
    10) die "Codex review JSON gate: Critical または decision=fail。safe-push は停止しました。" ;;
    11) die "Codex review JSON gate: Important / needs_human_review。ALLOW_IMPORTANT=true が無いので停止しました。" ;;
    12)
      die "Codex が skipped/failed に相当です（latest.json が executed ではない）、または門番ファイルが欠落しています。"
      ;;
    13)
      die "Codex JSON のパースに失敗しました。.ai/reviews/latest.json と make codex-review を確認してください。"
      ;;
    14)
      die "Codex JSON が不正か decision と配列が矛盾しています。latest.json を確認してください。"
      ;;
    *)
      die "Codex JSON checker internal error (exit ${rc})"
      ;;
  esac
}

run_ai_check() {
  echo "==> make ai-check (PYTHON=${PYTHON})"
  make ai-check PYTHON="${PYTHON}"
}

run_git_diff_check() {
  echo "==> git diff --check"
  git -C "${ROOT}" diff --check
}

run_selective_stage_dry_run_list() {
  echo "==> DRY_RUN: selective stage (git status --short --untracked-files=all) — same paths as real safe-push"
  ensure_index_clean_or_die
  local paths
  paths="$(collect_safe_push_stage_paths_or_die)"
  if [[ -z "${paths}" ]]; then
    echo "(none)"
  else
    printf '%s\n' "${paths}"
  fi
  echo "==> DRY_RUN: would run: git add -- <paths above> (not executed); then commit/push"
}

echo "safe-push root: ${ROOT}"

echo "==> forbidden path scan (pre-ai-check, git status --short --untracked-files=all)"
check_git_status_paths_or_die "pre-ai-check"

run_ai_check
run_git_diff_check

echo "==> forbidden path scan (post-ai-check, git status --short --untracked-files=all)"
check_git_status_paths_or_die "post-ai-check"

analyze_codex_review

if [[ "${DRY_RUN}" == "true" ]] || [[ "${DRY_RUN}" == "True" ]] || [[ "${DRY_RUN}" == "1" ]]; then
  run_selective_stage_dry_run_list
  echo "==> DRY_RUN: skipping git add / commit / push"
  exit 0
fi

ensure_index_clean_or_die

STAGE_TEXT="$(collect_safe_push_stage_paths_or_die)"
if [[ -z "${STAGE_TEXT}" ]]; then
  die "no paths to stage (working tree clean or only ignored entries); nothing to commit"
fi

STAGE_PATHS=()
while IFS= read -r _p || [[ -n "${_p}" ]]; do
  [[ -z "${_p}" ]] && continue
  STAGE_PATHS+=("${_p}")
done < <(printf '%s\n' "${STAGE_TEXT}")

printf '%s\n' "${STAGE_PATHS[@]}" | check_paths_stream_or_die "pre-git-add"

echo "==> git add -- (selective, status-derived paths)"
git -C "${ROOT}" add -- "${STAGE_PATHS[@]}"

echo "==> forbidden path scan (staged)"
check_paths_stream_or_die "staged" < <(git -C "${ROOT}" diff --cached --name-only | sort -u)

echo "==> git commit -m ..."
git -C "${ROOT}" commit -m "${COMMIT_MSG}"

echo "==> git push"
git -C "${ROOT}" push

echo "safe-push: done."
