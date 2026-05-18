#!/bin/bash
set -euo pipefail

REPO="$(git rev-parse --show-toplevel)"
cd "$REPO"

[ "$(git branch --show-current)" != "main" ] || { echo "❌ main-gate must run on a feature branch before PR"; exit 1; }

git fetch origin main --quiet
git merge-base --is-ancestor origin/main HEAD || { echo "❌ Branch is behind or diverged from origin/main"; exit 1; }

PYTHON=${PYTHON:-.venv/bin/python}

echo "▶ pytest..."
"$PYTHON" -m pytest -q --tb=line

echo "▶ agent-final-check..."
PYTHON="$PYTHON" make -s agent-final-check

echo "▶ git diff --check..."
git diff --check origin/main...HEAD

DIFF=$(git diff origin/main...HEAD)
# Gate definition files may mention patterns literally; scan product/docs changes only.
DIFF_SCAN=$(git diff origin/main...HEAD -- . ":(exclude).pre-commit-config.yaml" ":(exclude)scripts/main_gate.sh")

echo "▶ secret scan..."
if echo "$DIFF_SCAN" | grep -qnE "AKIA[0-9A-Z]{16}|SECRET\s*=|TOKEN\s*=|JQUANTS_API_KEY\s*=|BEGIN .*PRIVATE KEY|sk-[A-Za-z0-9]{20}"; then
  echo "❌ Secret-like pattern detected in diff"
  exit 1
fi

echo "▶ network/cache scan..."
if echo "$DIFF_SCAN" | grep -qnE "JQUANTS_ALLOW_LIVE_HTTP\s*=\s*[Tt]rue|execute-cache-write"; then
  echo "❌ Live HTTP / cache write enable pattern detected in diff"
  exit 1
fi

SENSITIVE=$(git diff --name-only origin/main...HEAD -- .github/ Makefile pyproject.toml || true)
if [ -n "$SENSITIVE" ]; then
  echo "⚠️ Sensitive files changed:"
  echo "$SENSITIVE" | sed 's/^/   /'
  echo "Review explicitly in PR."
fi

echo "✅ main-gate: all checks passed"
