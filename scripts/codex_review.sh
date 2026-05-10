#!/usr/bin/env bash
# Laputa Alpha OS — run Codex CLI review and save markdown to .ai/reviews/latest.md
# Does not: git add/commit/push, source .env, or pass credentials into the prompt.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p .ai/reviews

OUT="${ROOT}/.ai/reviews/latest.md"
STAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

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
  } >"$OUT"
  echo "codex-review: Codex CLI が見つからないためスキップしました。説明は ${OUT} を参照してください。" >&2
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
} >"$OUT"

# Codex CLI v0.130+: `-a/--ask-for-approval` と `-s/--sandbox` は `exec` の前に置く。
# `--ephemeral` / `-C` は `exec` サブコマンド側のオプション。
set +e
{
  cat <<'P1'
You are a senior reviewer for the Laputa Alpha OS (invest-alpha-os) repository.

STRICT RULES FOR THIS RUN:
- Read-only review: respond with markdown only. Do not apply or suggest applying patches/commands that modify the repo.
- Do NOT read, open, or ask anyone to open: .env, .env.* (except .env.example), credentials.json, token.json, secrets/, keys, or real data under outputs/.
- Do not run or suggest running live trading, external paid APIs with real keys, or curl/fetch against private endpoints for verification.
- Base conclusions on safe repo areas (src, tests, docs, .github, Makefile, config templates) and the git context block below.

CONTEXT — git status --short and git diff --stat only (automation does not inject file contents from secret paths):

P1
  printf '%s\n\n%s\n' "${GS}" "${GDS}"
  cat <<'P2'

Review focus (use Critical / Important / Minor where helpful):
1. Phase scope: changes must not exceed the intended phase.
2. No secrets: .env, credentials, tokens, real outputs data must not be committed or pasted into docs.
3. GitHub Actions: anything likely to break CI?
4. make verify: is the layout still consistent with a green verify?
5. Live API: real HTTP/API must not run unexpectedly (e.g. explicit CLI flags + env gates).
6. Logging/CLI: no tokens, passwords, or raw auth responses in logs or stdout.
7. Separation: config vs docs vs src responsibilities stay clear.

End with a short summary and recommended next steps.
P2
} | codex --sandbox read-only --ask-for-approval never exec --ephemeral -C "${ROOT}" - >>"$OUT"
CODEX_RC=$?
set -e

if [[ "${CODEX_RC}" -ne 0 ]]; then
  {
    echo
    echo "---"
    echo "*Codex が終了コード ${CODEX_RC} で終了しました（詳細はターミナル stderr を参照）。*"
  } >>"$OUT"
fi

exit "${CODEX_RC}"
