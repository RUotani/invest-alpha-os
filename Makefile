PYTHON ?= python

# macOS は `python` が無いことが多く、標準ゲートだけだと CI/ローカルで失敗しやすい。
# `.venv/bin/python` があれば明示的パスへ寄せる。`PYTHON=... make` で上書きした場合はそのまま尊重する。
VENVP := $(CURDIR)/.venv/bin/python
ifneq ($(wildcard $(VENVP)),)
  ifeq ($(PYTHON),python)
    PYTHON := $(VENVP)
  endif
else
  ifeq ($(PYTHON),python)
    PYTHON := python3
  endif
endif

# safe-push 直下の bash は環境変数を継承する。commit message は Makefile で展開せず SAFE_PUSH_MSG で渡す。
export PYTHON
export ALLOW_IMPORTANT

.PHONY: setup test status config-check daily pack risks verify codex-review ai-check safe-push safe-push-dry-run \
	env-doctor daily-check jquants-smoke-dry-run jquants-smoke-live post-push-check ops-check

setup:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e .[dev]

test:
	$(PYTHON) -m pytest -q

status:
	$(PYTHON) -m invis_alpha_os.cli.main status

config-check:
	$(PYTHON) -m invis_alpha_os.cli.main config-check

daily:
	$(PYTHON) -m invis_alpha_os.cli.main daily

pack:
	$(PYTHON) -m invis_alpha_os.cli.main pack --ticker 7011

risks:
	$(PYTHON) -m invis_alpha_os.cli.main risks

verify:
	@echo "==> [1/8] make test"
	$(MAKE) test
	@echo "==> [2/8] status"
	$(PYTHON) -m invis_alpha_os.cli.main status
	@echo "==> [3/8] config-check"
	$(PYTHON) -m invis_alpha_os.cli.main config-check
	@echo "==> [4/8] snapshot watchlist"
	$(PYTHON) -m invis_alpha_os.cli.main snapshot watchlist
	@echo "==> [5/8] daily"
	$(PYTHON) -m invis_alpha_os.cli.main daily
	@echo "==> [6/8] pack --ticker 7011"
	$(PYTHON) -m invis_alpha_os.cli.main pack --ticker 7011
	@echo "==> [7/8] risks"
	$(PYTHON) -m invis_alpha_os.cli.main risks
	@echo "==> [8/8] git status --short"
	git status --short

codex-review:
	bash scripts/codex_review.sh

ai-check:
	$(MAKE) verify PYTHON="$(PYTHON)"
	$(MAKE) codex-review
	git status --short

# safe-push / dry-run: 門番は .ai/reviews/latest.json のみ（review_run_status=executed 必須）。
# Forbidden paths: git status で pre / post の2回 + staged で1回（ai-check より前から）。failed/skipped と ALLOW_IMPORTANT の例外は変更なし。
# Staging はリポジトリ全体の一括 index add を使わず、同じ status 由来の候補に対する `git add --` のみ（clean index 前提・DRY_RUN は add しない）。
# Important / needs_human_review を通すのは ALLOW_IMPORTANT=true を人間が明示した場合のみ。
# commit message は Makefile レシピ内では展開しない（シェル注入リスク回避）。SAFE_PUSH_MSG はスクリプトが検証して読む。
safe-push:
	bash scripts/safe_commit_push.sh

safe-push-dry-run:
	DRY_RUN=true bash scripts/safe_commit_push.sh

# --- Local ops shortcuts (DevOps Task 2) — no secrets printed; ops-check avoids live HTTP. -----------------
env-doctor:
	bash scripts/env_doctor.sh

daily-check:
	bash scripts/daily_check.sh

# DATE=YYYY-MM-DD LIMIT=N [PYTHON=.venv/bin/python] make jquants-smoke-dry-run — dry-run + --save-summary only.
jquants-smoke-dry-run:
	@test -n "$(DATE)" || (echo 'DATE is required (e.g. DATE=2024-02-19)' >&2 && exit 1)
	@test -n "$(LIMIT)" || (echo 'LIMIT is required (e.g. LIMIT=3)' >&2 && exit 1)
	bash scripts/jquants_smoke.sh dry-run "$(DATE)" "$(LIMIT)"

# CONFIRM_LIVE_HTTP=YES DATE=... LIMIT=... [PYTHON=.venv/bin/python] make jquants-smoke-live — one-shot live + save-summary.
jquants-smoke-live:
	@test "$(CONFIRM_LIVE_HTTP)" = "YES" || (echo 'Set CONFIRM_LIVE_HTTP=YES to enable live HTTP (human gate).' >&2 && exit 1)
	@test -n "$(DATE)" || (echo 'DATE is required' >&2 && exit 1)
	@test -n "$(LIMIT)" || (echo 'LIMIT is required' >&2 && exit 1)
	bash scripts/jquants_smoke.sh live "$(DATE)" "$(LIMIT)"

post-push-check:
	bash scripts/post_push_check.sh

ops-check: env-doctor daily-check post-push-check

