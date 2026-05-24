# Program Review / Cursor Fix Plan — 2026-05-24

## 3行サマリー

- 判定: **APPROVE_WITH_ACTION_ITEMS**。`pytest` は **1020 passed**、read-only smoke も通るが、lint 失敗・ops smoke の弱い判定・handoff/STATE の stale 化が残る。
- 最優先修正: **ops smoke の fail 条件を実質化**、**ruff 56件の解消**、**STATE/handoff の現状同期**。
- Cursor には **1 PR = 1 修正領域**で依頼する。live HTTP、cache write、Gmail、operator 新機能追加は触らない。

---

## Review Scope

対象 checkout:

- branch: `work/product-forward-event-date-20260524`
- HEAD: `7547b4d`
- `origin/main`: `7547b4d`
- working tree: **dirty**。既存の未コミット変更あり（このレビューでは上書き禁止）
- untracked: `.agent/ops_smoke/`, `src/invis_alpha_os/product/forward_event_resolution.py`, `tests/test_forward_event_resolution.py`

Dirty files observed:

```text
M docs/160_product_weekly_operator_one_pager.md
M docs/161_product_forward_validation_fresh_log_guidance.md
M src/invis_alpha_os/cli/main.py
M src/invis_alpha_os/observation/us_peer_sync_batch.py
M src/invis_alpha_os/observation/us_peer_sync_note.py
M src/invis_alpha_os/observation/us_signal_note.py
M src/invis_alpha_os/product/peer_sync_forward_validation.py
M src/invis_alpha_os/product/us_forward_return_validation.py
?? .agent/ops_smoke/
?? src/invis_alpha_os/product/forward_event_resolution.py
?? tests/test_forward_event_resolution.py
```

実行した検証:

```bash
.venv/bin/python -m pytest -q
# 1020 passed in 10.02s

.venv/bin/python -m invis_alpha_os.cli.main status
.venv/bin/python -m invis_alpha_os.cli.main config-check
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync --format markdown
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --with-peer-sync --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate jp-peer-sync-readiness --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot portfolio-observation-summary --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown

.venv/bin/python -m ruff check src tests
# failed: 56 errors
```

禁止事項は実行していない:

- live HTTP
- cache write
- Gmail send
- push / merge / branch delete / force push
- secrets / `.env` read or output

---

## Current Health

| Area | Status | Evidence |
| --- | --- | --- |
| tests | OK | `1020 passed` |
| config | OK | `config-check: OK` |
| observation mode | OK | `status` prints Observation Only / No Auto Trading |
| ops smoke | superficially OK | `all_ok: True`, but fail logic is weak |
| observation health | usable | 18 rows, parse errors 0, forward sample empty due fresh logs |
| peer_sync | partial | US pairs diverged, JP edges cache-ready but current peer_sync report still shows JP insufficient aligned sessions |
| portfolio | empty | 0 shadow positions, portfolio progress remains `[要確認]%` |
| lint | NG | `ruff check src tests` has 56 errors |
| docs/state | stale | handoff and STATE still mention old branch / old origin/main / old test count |
| working tree | dirty | Cursor must preserve existing user/agent changes |

---

## Critical / Important Findings

### 1. Important: `validate ops-smoke` can report OK even when core checks are degraded

Files:

- `src/invis_alpha_os/product/ops_smoke_report.py:63`
- `src/invis_alpha_os/product/ops_smoke_report.py:73`
- `src/invis_alpha_os/product/ops_smoke_report.py:84`

Problem:

`watchlist_manifest` is OK when `entries > 0 or missing >= 0`. Since `missing >= 0` is always true, this cannot fail. `signal_quality_snapshot` is OK when `sig_total == 0 or sig_ok >= 0`, which is also effectively always true.

Risk:

The weekly operator smoke can show `all_ok: True` even if cache coverage or signal quality is degraded. This is a false-green risk.

Recommended fix:

- `watchlist_manifest`: warn/fail when `entries == 0` or `missing_cache_symbols` is non-empty, depending on intended strictness.
- `signal_quality_snapshot`: warn/fail when `sig_total == 0` or `sig_ok < sig_total`.
- Add tests in `tests/test_ops_smoke_report.py` for:
  - missing cache produces `warn` or `fail`
  - zero entries does not produce OK
  - partial signal quality does not produce OK

Suggested severity: **Important**

---

### 2. Important: lint is not clean although tests are green

Command:

```bash
.venv/bin/python -m ruff check src tests
```

Result:

- 56 errors
- examples:
  - unused imports in `src/invis_alpha_os/cli/main.py`
  - unused `pr_range` in `src/invis_alpha_os/operator/operator_autopilot.py`
  - `F821 Undefined name Any` in `tests/test_us_provider_manual_live_batch_smoke.py`
  - `E402` import ordering in `src/invis_alpha_os/operator/dev_loop.py`
  - many unused imports in tests

Risk:

`pyproject.toml` includes ruff as a dev dependency, but current `make verify` does not run ruff. This allows code hygiene regressions to accumulate.

Recommended fix:

- First PR: run `ruff check src tests --fix` only for safe auto-fixable items, then manually fix remaining non-behavioral issues.
- Do **not** add ruff to `make verify` in the same PR unless the tree is clean and the user explicitly wants a stricter gate.
- Add a follow-up PR to introduce `make lint` and optionally `make verify` integration after noise is removed.

Suggested severity: **Important**

---

### 3. Important: project state docs are stale and can mislead agents

Files:

- `.agent/product_peer_sync_portfolio_longrun_handoff_20260524.md:11`
- `.agent/product_peer_sync_portfolio_longrun_handoff_20260524.md:12`
- `.agent/product_peer_sync_portfolio_longrun_handoff_20260524.md:13`
- `.agent/product_peer_sync_portfolio_longrun_handoff_20260524.md:14`
- `.agent/product_peer_sync_portfolio_longrun_handoff_20260524.md:42`
- `.agent/product_peer_sync_portfolio_longrun_handoff_20260524.md:58`
- `STATE.md:6`
- `STATE.md:31`

Observed stale values:

- handoff says `origin/main` is `4402dae`; current local `origin/main` is `7547b4d`
- handoff says branch is `work/product-ops-smoke-and-continue-20260524`; current branch is `work/product-forward-event-date-20260524`
- handoff says PR #218 is pending; current history has #226 at HEAD
- handoff says tests are `999 passed`; current tests are `1020 passed`
- `STATE.md` says `origin/main: a328e29`; current is `7547b4d`

Risk:

Cursor/Codex agents can base work on obsolete PR and branch state.

Recommended fix:

- Update `.agent/product_peer_sync_portfolio_longrun_handoff_20260524.md` or mark it archived/stale.
- Update `STATE.md` to current `origin/main`, current merged range, and current test count.
- Keep `portfolio/` as `[要確認]%` unless scope includes defining the portfolio readiness rubric.

Suggested severity: **Important**

---

### 4. Important: `.agent/ops_smoke/` is untracked and not ignored

Evidence:

```bash
git status --short --ignored .agent outputs .ai
# ?? .agent/ops_smoke/
```

Files currently under the untracked directory:

- `.agent/ops_smoke/01_validate_peer_sync.md`
- `.agent/ops_smoke/02_portfolio_observation_summary.json`
- `.agent/ops_smoke/03_weekly_us_observation_peer_sync.md`

Risk:

These look like generated local operator artifacts. If not intentionally committed, they should not remain as untracked noise. If they are intended as evidence, they should be moved to `reports/2026-05-24/` and reviewed before commit.

Recommended fix:

- Decide one path:
  - generated/local only: add `.agent/ops_smoke/` to `.gitignore`
  - evidence to commit: move sanitized files to `reports/2026-05-24/`
- Do not blindly commit `.agent/ops_smoke/`.

Suggested severity: **Important**

---

### 5. Minor: `snapshot observation-health` repeats next commands

File:

- `src/invis_alpha_os/product/observation_health.py:111`
- `src/invis_alpha_os/product/observation_health.py:120`

Observed output repeats `log us-signals-summary`.

Risk:

Low, but operator output becomes noisy and copy-paste instructions are less clean.

Recommended fix:

- Deduplicate `next_commands` while preserving order.
- Add a small assertion in `tests/test_observation_health.py`.

Suggested severity: **Minor**

---

### 6. Minor: portfolio progress remains undefined despite new summary tooling

Files:

- `STATE.md:16`
- `docs/154_product_portfolio_progress_proposal.md:3`
- `src/invis_alpha_os/product/portfolio_observation_summary.py:43`

Current state:

- `snapshot portfolio-observation-summary` works.
- Shadow portfolio has 0 positions.
- `portfolio/` progress is still `[要確認]%`.

Risk:

This is not a code bug. It is a product-management gap: readiness is not measurable yet.

Recommended fix:

- Define a portfolio readiness rubric in `docs/154`.
- Keep implementation read-only.
- Do not add trading recommendation logic.

Suggested severity: **Minor**

---

## Safety Assessment

Good:

- Default status remains Observation Only / No Auto Trading.
- `outputs/**`, `.env`, token/credentials are gitignored.
- J-Quants and US provider live/cache write paths are gated.
- `weekly-us-observation --dry-run --with-peer-sync` is read-only.
- `validate jp-peer-sync-readiness` explicitly says live J-Quants cache ingest requires approval.

Needs attention:

- `.agent/ops_smoke/` is not ignored.
- `ruff` is not part of the active green gate.
- `ops-smoke` fail conditions are too permissive.
- `STATE.md` and handoff are stale.

---

## Recommended Cursor PR Sequence

### PR 1 — Fix false-green ops smoke

Scope:

- `src/invis_alpha_os/product/ops_smoke_report.py`
- `tests/test_ops_smoke_report.py`

Do:

- Make `watchlist_manifest` and `signal_quality_snapshot` statuses meaningful.
- Add negative tests.
- Keep CLI output compact.

Do not:

- Change daily/signals defaults.
- Touch operator runner.
- Run live HTTP or write caches.

Verification:

```bash
.venv/bin/python -m pytest tests/test_ops_smoke_report.py tests/test_product_weekly_us_observation.py -q
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format markdown
```

### PR 2 — Clean ruff without behavior changes

Scope:

- non-behavioral import/order/name cleanup only
- no product logic changes

Verification:

```bash
.venv/bin/python -m ruff check src tests
.venv/bin/python -m pytest -q
```

### PR 3 — Sync state/handoff and artifact policy

Scope:

- `STATE.md`
- `.agent/product_peer_sync_portfolio_longrun_handoff_20260524.md`
- `.gitignore` or move `.agent/ops_smoke/*` to `reports/2026-05-24/`

Verification:

```bash
git status --short --ignored .agent outputs .ai
.venv/bin/python -m pytest tests/test_agent_handoff.py tests/test_security_invariants.py -q
```

### PR 4 — Deduplicate operator next commands

Scope:

- `src/invis_alpha_os/product/observation_health.py`
- tests around observation health output

Verification:

```bash
.venv/bin/python -m pytest tests/test_observation_health.py -q
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
```

### PR 5 — Define portfolio readiness rubric

Scope:

- docs first: `docs/154_product_portfolio_progress_proposal.md`
- optionally `STATE.md`

Do:

- Define readiness criteria for portfolio observation mode.
- Keep `[要確認]%` until criteria are accepted.

Do not:

- Implement buy/sell recommendation.
- Modify trading recommendation logic.

---

## Cursor Agent Prompt

```text
You are working in RUotani/invest-alpha-os.

Read first:
- RULES.md
- STATE.md
- reports/2026-05-24/program_review_cursor_fix_plan_20260524.md

Task:
Implement PR 1 only: fix false-green ops smoke.

Branch:
work/fix-ops-smoke-real-status-20260524

Allowed files:
- src/invis_alpha_os/product/ops_smoke_report.py
- tests/test_ops_smoke_report.py

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
- Make watchlist_manifest status non-OK when there are zero entries or missing cache symbols.
- Make signal_quality_snapshot status non-OK when signals_ok < signals_total or total is zero.
- Keep output compact and observation-only.
- Add regression tests for zero entries, missing cache, and partial signal quality.

Verification:
.venv/bin/python -m pytest tests/test_ops_smoke_report.py tests/test_product_weekly_us_observation.py -q
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format markdown

Return:
- files changed
- test results
- whether any safety constraints were touched
```

---

## Final Recommendation

Cursor に最初に渡すべきは **PR 1: ops smoke false-green 修正**。  
理由: テスト green でも operator が誤って安全判定する可能性があり、他の修正より期待値が高い。
