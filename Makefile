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

# jq-cache-live / jq-refresh が使う ops JSON 出力先をテストなどでオーバーライドするときのみ設定。
ifdef JQ_OPS_OUTPUT_DIR
export JQ_OPS_OUTPUT_DIR
endif

.PHONY: setup test status config-check daily pack risks verify codex-review ai-check safe-push safe-push-dry-run \
	env-doctor daily-check jquants-smoke-dry-run jquants-smoke-live post-push-check ops-check \
	jq-cache-preview jq-cache-live jq-cache-live-codes jq-refresh-workflow \
	signals-cache-only daily-momentum-check investment-os-coverage ship ops-snapshot agent-final-check \
	us-watchlist-preview us-cache-fixture-import us-momentum-check

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

agent-final-check:
	PYTHON="$(PYTHON)" bash scripts/agent_final_check.sh

us-watchlist-preview:
	$(PYTHON) -m invis_alpha_os.cli.main us-watchlist-preview

# Main R1: local US OHLCV fixtures → outputs/market_data/us_daily_bars (no HTTP).
FIX_US_DAILY := $(CURDIR)/tests/fixtures/us_daily_bars

us-cache-fixture-import:
	$(PYTHON) -m invis_alpha_os.cli.main debug us-daily-bars-cache-import --symbol MSFT --bars-file "$(FIX_US_DAILY)/MSFT.json" --asset-class us_equity --source local_fixture --write-cache
	$(PYTHON) -m invis_alpha_os.cli.main debug us-daily-bars-cache-import --symbol GOOGL --bars-file "$(FIX_US_DAILY)/GOOGL.json" --asset-class us_equity --source local_fixture --write-cache
	$(PYTHON) -m invis_alpha_os.cli.main debug us-daily-bars-cache-import --symbol GLDM --bars-file "$(FIX_US_DAILY)/GLDM.json" --asset-class us_etf --source local_fixture --write-cache

us-momentum-check:
	@if [ ! -f "$(CURDIR)/outputs/market_data/us_daily_bars/MSFT.json" ] || \
	     [ ! -f "$(CURDIR)/outputs/market_data/us_daily_bars/GOOGL.json" ] || \
	     [ ! -f "$(CURDIR)/outputs/market_data/us_daily_bars/GLDM.json" ]; then \
		$(MAKE) us-cache-fixture-import PYTHON="$(PYTHON)"; \
	fi
	$(PYTHON) "$(CURDIR)/scripts/us_momentum_check.py"

# --- Main K: short ops (no secrets in repo; jq-cache-live uses real HTTP + quota when run) --------------------
# make jq-cache-preview FROM=2024-02-18 TO=2026-02-17 [LIMIT=11]  — preview only, no HTTP
jq-cache-preview:
	@test -n "$(FROM)" || (echo 'FROM is required (YYYY-MM-DD)' >&2 && exit 1)
	@test -n "$(TO)" || (echo 'TO is required (YYYY-MM-DD)' >&2 && exit 1)
	FROM="$(FROM)" TO="$(TO)" LIMIT="$(LIMIT)" CODES="$(CODES)" PYTHON="$(PYTHON)" bash scripts/jq_watchlist_bars_cache_preview.sh

# Live + write cache: requires CONFIRM_LIVE_HTTP=YES (same as CLI for any bulk --live) + sets allow-live.
# LIMIT is required unless CODES is set (comma-separated wire codes for retry / subsets).
jq-cache-live:
	@test "$(CONFIRM_LIVE_HTTP)" = "YES" || (echo 'CONFIRM_LIVE_HTTP=YES required' >&2 && exit 2)
	@test -n "$(FROM)" || (echo 'FROM is required' >&2 && exit 1)
	@test -n "$(TO)" || (echo 'TO is required' >&2 && exit 1)
	@test -n "$(LIMIT)" -o -n "$(CODES)" || (echo 'LIMIT or CODES is required' >&2 && exit 1)
	FROM="$(FROM)" TO="$(TO)" LIMIT="$(LIMIT)" CODES="$(CODES)" CONFIRM_LIVE_HTTP="$(CONFIRM_LIVE_HTTP)" PYTHON="$(PYTHON)" bash scripts/jq_watchlist_bars_cache_live.sh

# Same as jq-cache-live but requires CODES=... (explicit failed-code retry path).
jq-cache-live-codes:
	@test "$(CONFIRM_LIVE_HTTP)" = "YES" || (echo 'CONFIRM_LIVE_HTTP=YES required' >&2 && exit 2)
	@test -n "$(FROM)" || (echo 'FROM is required' >&2 && exit 1)
	@test -n "$(TO)" || (echo 'TO is required' >&2 && exit 1)
	@test -n "$(CODES)" || (echo 'CODES is required (comma-separated wire codes)' >&2 && exit 1)
	@$(MAKE) jq-cache-live FROM="$(FROM)" TO="$(TO)" CODES="$(CODES)" CONFIRM_LIVE_HTTP="$(CONFIRM_LIVE_HTTP)" PYTHON="$(PYTHON)" $(if $(LIMIT),LIMIT="$(LIMIT)")

# Preview → live (ops JSON) → signals + momentum only when verdict allows (ALLOW_PARTIAL_CACHE for partial_success).
jq-refresh-workflow:
	@test -n "$(FROM)" || (echo 'FROM is required' >&2 && exit 1)
	@test -n "$(TO)" || (echo 'TO is required' >&2 && exit 1)
	@test "$(CONFIRM_LIVE_HTTP)" = "YES" || (echo 'CONFIRM_LIVE_HTTP=YES required' >&2 && exit 2)
	@test -n "$(LIMIT)" -o -n "$(CODES)" || (echo 'LIMIT or CODES is required' >&2 && exit 1)
	FROM="$(FROM)" TO="$(TO)" LIMIT="$(LIMIT)" CODES="$(CODES)" CONFIRM_LIVE_HTTP="$(CONFIRM_LIVE_HTTP)" ALLOW_PARTIAL_CACHE="$(ALLOW_PARTIAL_CACHE)" PYTHON="$(PYTHON)" bash scripts/jq_refresh_workflow.sh

# LIMIT=N make signals-cache-only
signals-cache-only:
	$(PYTHON) -m invis_alpha_os.cli.main signals --source cache-only --dry-run $(if $(LIMIT),--limit $(LIMIT),)

daily-momentum-check:
	PYTHON="$(PYTHON)" bash scripts/daily_momentum_check.sh

# Main Q0: print Investment OS coverage map (no HTTP, markdown only).
investment-os-coverage:
	@cat $(CURDIR)/docs/10_investment_os_coverage_map.md

# Local ops JSON under outputs/ops/ (gitignored; no secrets)
ops-snapshot:
	@bash -c 'ec=0; $(PYTHON) -m pytest -q || ec=$$?; $(PYTHON) scripts/ops_write_json.py --mode pytest --pytest-exit $$ec; exit $$ec'

# SAFE_PUSH_MSG="..." make ship
ship:
	@test -n "$${SAFE_PUSH_MSG}" || (echo 'SAFE_PUSH_MSG is required' >&2 && exit 1)
	$(MAKE) test PYTHON="$(PYTHON)"
	$(MAKE) safe-push
	$(MAKE) post-push-check
	$(PYTHON) scripts/ops_write_json.py --mode ship

