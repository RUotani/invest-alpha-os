# Cursor Follow-up Instructions — PR2 to PR5

> **Status: COMPLETED** (2026-05-24) — PR2 #229, PR3–5 #230, fix plan #228. main `d3bd10d`.

## 3行サマリー

- PR2 は現在の branch `work/fix-ruff-clean-20260524` で実装済み相当。`ruff check src tests` は **pass**、`pytest` は **1029 passed**。
- 次に推奨する実作業は **PR3: state/handoff と artifact policy の同期**、**PR4: observation-health next commands 重複除去**、**PR5: portfolio readiness rubric 定義**。
- Cursor には **1 PR = 1 領域**で渡す。live HTTP、cache write、Gmail、operator 新機能追加、投資推奨ロジック変更は禁止。

---

## Current Status

確認日時: 2026-05-24 JST

```text
branch: work/fix-ruff-clean-20260524
HEAD: 0289e73 chore: clean ruff lint across src and tests
base origin/main: fc2e85b fix: make validate ops-smoke status checks meaningful (#228)
working tree untracked:
  ?? .agent/ops_smoke/
  ?? reports/2026-05-24/program_review_cursor_fix_plan_20260524.md
  ?? reports/2026-05-24/cursor_followup_pr2_to_pr5_instructions_20260524.md
```

Verification:

```bash
.venv/bin/python -m ruff check src tests
# All checks passed!

.venv/bin/python -m pytest -q
# 1029 passed in 7.71s
```

---

## Recommendation

| Item | Status | Recommendation |
| --- | --- | --- |
| PR2 — ruff clean | 実装済み相当 | Review / merge 待ち。追加実装は不要 |
| PR3 — state/handoff + artifact policy | 推奨 | 実施する。次の最優先 |
| PR4 — observation-health next commands dedupe | 推奨 | PR3 後に実施 |
| PR5 — portfolio readiness rubric | 推奨 | docs-only 優先で実施 |

---

## PR2 — Ruff Clean

### 判定

**実施済み相当。新規 Cursor 作業は不要。**

現在 branch `work/fix-ruff-clean-20260524` で:

- `ruff check src tests`: pass
- `pytest -q`: 1029 passed

### 人間レビュー観点

- lint cleanup が behavior change を含んでいないか
- `src/invis_alpha_os/operator/*` の変更が単純な import/order/unused cleanup に留まるか
- tests の import cleanup がテスト意味を変えていないか

### PR2 review prompt

```text
Review branch work/fix-ruff-clean-20260524.

Focus:
- Confirm this is lint-only / non-behavioral cleanup.
- Confirm ruff passes.
- Confirm pytest passes.
- Confirm no live HTTP, cache write, Gmail, push, merge, or operator feature addition.

Verification:
.venv/bin/python -m ruff check src tests
.venv/bin/python -m pytest -q

Return:
- APPROVE / REQUEST_CHANGES
- any behavior-change concerns
- test results
```

---

## PR3 — Sync State/Handoff and Artifact Policy

### 判定

**実施推奨。**

理由:

- `.agent/product_peer_sync_portfolio_longrun_handoff_20260524.md` と `STATE.md` が古い branch / main SHA / PR 状態 / test count を含む。
- `.agent/ops_smoke/` が untracked のまま残っており、生成物か evidence かの扱いが曖昧。
- Agent が stale な handoff を読むと、古い PR 前提で作業するリスクがある。

### Cursor Prompt

```text
You are working in RUotani/invest-alpha-os.

Read first:
- RULES.md
- STATE.md
- reports/2026-05-24/program_review_cursor_fix_plan_20260524.md
- reports/2026-05-24/cursor_followup_pr2_to_pr5_instructions_20260524.md

Task:
Implement PR3 only: sync current state/handoff and decide artifact policy for .agent/ops_smoke/.

Branch:
work/sync-state-handoff-artifacts-20260524

Allowed files:
- STATE.md
- .agent/product_peer_sync_portfolio_longrun_handoff_20260524.md
- .gitignore
- reports/2026-05-24/* only if moving sanitized evidence out of .agent/ops_smoke/

Do not touch:
- src/invis_alpha_os/operator/*
- src/invis_alpha_os/signals/*
- src/invis_alpha_os/risk/*
- src/invis_alpha_os/portfolio/*
- pyproject.toml
- Makefile
- .github/workflows/*
- outputs/**
- .env, credentials.json, token.json

Safety constraints:
- Do not run live HTTP.
- Do not write market cache.
- Do not send Gmail.
- Do not push, merge, delete branches, or force push.
- Do not change daily/signals default behavior.

Implementation requirements:
1. Update STATE.md to current origin/main and current merged PR state.
2. Update or clearly mark .agent/product_peer_sync_portfolio_longrun_handoff_20260524.md as stale/archived.
3. Resolve .agent/ops_smoke/ policy:
   - If local generated artifact: add .agent/ops_smoke/ to .gitignore.
   - If evidence to keep: move sanitized files to reports/2026-05-24/ and leave .agent/ clean.
4. Keep portfolio progress as [要確認]% unless this PR explicitly defines the rubric.

Verification:
git status --short --ignored .agent outputs .ai
.venv/bin/python -m pytest tests/test_agent_handoff.py tests/test_security_invariants.py -q
.venv/bin/python -m ruff check src tests

Return:
- files changed
- artifact policy decision
- test results
- safety constraints touched: yes/no
```

---

## PR4 — Deduplicate Observation Health Next Commands

### 判定

**実施推奨。**

理由:

- `snapshot observation-health --format markdown` の `Next commands` に重複が出る。
- operator output の品質改善であり、挙動リスクは低い。

### Cursor Prompt

```text
You are working in RUotani/invest-alpha-os.

Read first:
- RULES.md
- STATE.md
- reports/2026-05-24/cursor_followup_pr2_to_pr5_instructions_20260524.md

Task:
Implement PR4 only: deduplicate snapshot observation-health next_commands while preserving order.

Branch:
work/dedupe-observation-health-next-commands-20260524

Allowed files:
- src/invis_alpha_os/product/observation_health.py
- tests/test_observation_health.py

Do not touch:
- src/invis_alpha_os/operator/*
- src/invis_alpha_os/signals/*
- src/invis_alpha_os/risk/*
- src/invis_alpha_os/portfolio/*
- Makefile
- pyproject.toml
- .github/workflows/*
- outputs/**
- .env, credentials.json, token.json

Safety constraints:
- Do not run live HTTP.
- Do not write market cache.
- Do not send Gmail.
- Do not push, merge, delete branches, or force push.
- Do not change daily/signals default behavior.

Implementation requirements:
1. Deduplicate observation health next_commands while preserving first occurrence order.
2. Keep output compact and observation-only.
3. Add or update tests so duplicate commands cannot regress.

Verification:
.venv/bin/python -m pytest tests/test_observation_health.py -q
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
.venv/bin/python -m ruff check src tests

Return:
- files changed
- before/after next_commands behavior
- test results
- safety constraints touched: yes/no
```

---

## PR5 — Define Portfolio Readiness Rubric

### 判定

**実施推奨。ただし docs-first。**

理由:

- `STATE.md` の `portfolio/` が `[要確認]%` のまま。
- `snapshot portfolio-observation-summary` は動くが、portfolio observation mode の readiness 基準が未定義。
- ここは投資ロジック本体に近いので、まず criteria を決めるのが安全。

### Cursor Prompt

```text
You are working in RUotani/invest-alpha-os.

Read first:
- RULES.md
- STATE.md
- docs/154_product_portfolio_progress_proposal.md
- reports/2026-05-24/cursor_followup_pr2_to_pr5_instructions_20260524.md

Task:
Implement PR5 only: define portfolio readiness rubric as docs-first work.

Branch:
work/portfolio-readiness-rubric-docs-20260524

Allowed files:
- docs/154_product_portfolio_progress_proposal.md
- STATE.md
- optionally tests/test_portfolio_observation_summary.py only if adding a doc/contract guard is necessary

Do not touch:
- src/invis_alpha_os/operator/*
- src/invis_alpha_os/signals/*
- src/invis_alpha_os/risk/*
- src/invis_alpha_os/portfolio/* unless explicitly requested later
- Makefile
- pyproject.toml
- .github/workflows/*
- outputs/**
- .env, credentials.json, token.json

Safety constraints:
- Do not add buy/sell recommendation logic.
- Do not change trading recommendation behavior.
- Do not run live HTTP.
- Do not write market cache.
- Do not send Gmail.
- Do not push, merge, delete branches, or force push.

Implementation requirements:
1. Define a portfolio readiness rubric using domain-specific stages, not a single vague total percent.
2. Keep `[要確認]` if the data needed to score readiness is not yet available.
3. Separate observation-only linkage from any future allocation/sizing logic.
4. Include explicit non-goals:
   - no trade execution
   - no NISA sell recommendation
   - no portfolio sizing automation
5. Update STATE.md only if the rubric allows a defensible domain-level progress line.

Verification:
.venv/bin/python -m pytest tests/test_portfolio_observation_summary.py -q
.venv/bin/python -m ruff check src tests

Return:
- files changed
- rubric summary
- whether STATE.md progress changed or remained [要確認]
- safety constraints touched: yes/no
```

---

## Recommended Order

1. Finish PR2 review/merge: `work/fix-ruff-clean-20260524`
2. PR3: state/handoff + `.agent/ops_smoke/` policy
3. PR4: observation-health next command dedupe
4. PR5: portfolio readiness rubric

PR3 should come before PR4/PR5 because stale state and artifact ambiguity can mislead subsequent agents.

