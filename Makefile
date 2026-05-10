PYTHON ?= python

# Prefer `.venv/bin/python` when Makefile left PYTHON at default; respect command line / env.
VENVP := $(CURDIR)/.venv/bin/python
ifeq ($(origin PYTHON),default)
  ifneq ($(wildcard $(VENVP)),)
    PYTHON := $(VENVP)
  else ifneq ($(shell command -v python3 2>/dev/null),)
    PYTHON := python3
  else
    PYTHON := python
  endif
endif

.PHONY: setup test status config-check daily pack risks verify codex-review ai-check

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

