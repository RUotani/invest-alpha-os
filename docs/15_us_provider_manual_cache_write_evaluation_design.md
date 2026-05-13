# US provider — manual cache-write evaluation safety design (**Main R6.5.0 design / R6.5.7 production write**)

> **Document control:** v1.0 Main R6.5.0 (design only) → v1.1 Main R6.5.1 (refusal scaffold implemented) → v1.7 Main R6.5.7 (production cache write implemented) → v1.7.1 Main R6.5.7.1 (docs operator alignment).

## 1. Purpose

**Main R6.5.0** anchors the **safety design and checklist** for future **manual, operator-approved, bounded cache-write evaluation** — a potential follow-on to **R6.4.1 bounded live HTTP preview**.

**R6.5.0 is documentation only.**
- **No implementation** in R6.5.0.
- **No cache write** added.
- **No CLI flags** changed.
- **No workflow changes**.

**Main R6.5.1** implements `--evaluate-cache-write` as a **refusal scaffold only**.
- The flag is recognized and all 6 refusal orderings are deterministic (see §11 below).
- **No actual cache write** in R6.5.1.
- **No live HTTP consumed** by the `--evaluate-cache-write` path.
- **No raw response stored**, **no API key value in output**.
- Actual cache-write implementation was staged through R6.5.2–R6.5.7; **R6.5.7 introduced `--execute-cache-write`** (limited manual production write — see §5 and §10).

Canonical neighbours:
- Live HTTP (R6.4.1): **`docs/14_us_provider_manual_live_batch_smoke_design.md`**
- Failure matrix / playbook: **`docs/12_us_provider_failure_operator_playbook.md`**
- Scheduled ingest (R6.6+): **`docs/13_us_provider_scheduled_ingest_design.md`**
- Provider plan: **`docs/11_us_market_data_provider_plan.md`**

---

## 2. Scope

**R6.5.1** implements `--evaluate-cache-write` as a **refusal scaffold only** (always exits 2). **R6.5.7** introduced `--execute-cache-write` as the limited manual production cache write (all 9 conditions required — see §4):

- **Manual, bounded, operator-approved** — one CLI invocation; no supervisor, no cron, no GitHub Actions `schedule:`.
- **After successful live preview** — only rows that returned `live_preview_ok` in a preceding R6.4.1 run are eligible for cache write.
- **Explicit flags required** — `--evaluate-cache-write` (R6.5.1 refusal scaffold) **and** `--execute-cache-write` (R6.5.7 production write) plus `CONFIRM_US_CACHE_WRITE=YES`.
- **No bulk production refresh** — not a substitute for scheduled ingest; watchlist-wide automation remains R6.6+.
- **No CI automation** — not wired into Makefile shortcuts, `verify`, `safe-push`, or `agent-final-check`.

---

## 3. Non-goals

**R6.5.0 does NOT:**

- Write cache (`save_us_daily_bars_cache` not called).
- Add any CLI flags or modify existing options.
- Modify any `src/` or `tests/` files.
- Run live HTTP.
- Store raw vendor responses.
- Write to `outputs/market_data/`.
- Add a `.github/workflows/` schedule.
- Widen `safe-push`, `verify`, or `agent-final-check` scope.

---

## 4. Safety contract

**R6.5.1** enforces these requirements as refusal checks (all exit 2). **R6.5.7** actual production cache write proceeds only if **all** of the following are true:

| Requirement | Notes |
|-------------|-------|
| `--live` | Intent flag; already required for R6.4.1. |
| `--preflight` | Gate validation; already required for R6.4.1. |
| `--execute-live-http` | Live HTTP must have been requested. |
| `--evaluate-cache-write` | R6.5.1 refusal scaffold (always refuses alone); required as prerequisite for `--execute-cache-write`. |
| `--execute-cache-write` | R6.5.7 production write flag; triggers actual `save_us_daily_bars_cache` via `stooq_live_preview_sanitized_bars`. |
| `CONFIRM_US_LIVE_HTTP=YES` | Same gate as R6.4.1. |
| `CONFIRM_US_MANUAL_BATCH_SMOKE=YES` | Same gate as R6.4.1. |
| `CONFIRM_US_CACHE_WRITE=YES` | Additional operator intent gate; checked by both payload builder and `stooq_live_preview_sanitized_bars`. |
| `--max-http > 0` | Bounded cap; same as R6.4.1. |
| Only `live_preview_ok` rows are eligible | `parse_error`, `transport_error`, `validation_error`, invalid, and capped rows are **never** eligible. |
| Sanitized bars only | Only bars passing the existing sanitized OHLCV writer validation may be written. |
| Raw vendor response is never written | Only sanitized row data reaches the cache writer. |
| API key value is never printed | `STOOQ_APIKEY` remains env-only. |
| Cache target is deterministic and under `outputs/market_data/us_daily_bars/` only | No arbitrary paths. |
| Never from CI / workflow / Makefile shortcut | Manual operator invocation only. |

---

## 5. CLI shape — R6.5.1 refusal scaffold / R6.5.7 production write (implemented)

**R6.5.1 refusal scaffold** — flag is implemented; always exits 2; no cache write; no live HTTP consumed:

```text
# R6.5.1 — flag recognized, always refused (exit 2)
python -m invis_alpha_os.cli.main debug us-provider-manual-live-batch-smoke \
  --symbols MSFT \
  --provider stooq_preview \
  --live \
  --preflight \
  --execute-live-http \
  --evaluate-cache-write \
  --max-http 1
```

`--evaluate-cache-write` is **implemented in R6.5.1** as a refusal scaffold (always exits 2). **`--execute-cache-write`** was added in **R6.5.7** as the actual production write flag — requires all 9 conditions (see §10). **Scheduled / unattended ingest remains R6.6+**; no Makefile / workflow / cron added.

---

## 6. Refusal rules — reason strings (R6.5.1 `--evaluate-cache-write`; R6.5.7 `--execute-cache-write`)

**R6.5.1 implemented** (all exit 2, no cache write, no live HTTP):

| Reason string | Trigger | Exit | Safety intent |
|---------------|---------|:----:|---------------|
| `manual_batch_cache_write_requires_live` | `--evaluate-cache-write` without `--live` | **2** | Live intent required. |
| `manual_batch_cache_write_requires_preflight` | Without `--preflight` | **2** | Preflight confirmation required. |
| `manual_batch_cache_write_requires_execute_live_http` | Without `--execute-live-http` | **2** | Live HTTP must be requested. |
| `manual_batch_smoke_live_http_not_confirmed` | `CONFIRM_US_LIVE_HTTP` or `CONFIRM_US_MANUAL_BATCH_SMOKE` not YES | **2** | Existing live/manual gates enforced. |
| `manual_batch_cache_write_requires_cache_gate` | `CONFIRM_US_CACHE_WRITE` not `YES` | **2** | Explicit operator gate. |
| `manual_batch_cache_write_not_enabled_in_r6_5_1` | All flags + all gates set | **2** | Full-gate scaffold refusal — no write in R6.5.1. |

**R6.5.7 `--execute-cache-write` refusal ordering** (implemented — all exit 2 before production write):

| Reason string | Trigger | Exit | Safety intent |
|---------------|---------|:----:|---------------|
| `manual_batch_execute_cache_write_requires_live` | `--execute-cache-write` without `--live` | **2** | Live intent required. |
| `manual_batch_execute_cache_write_requires_preflight` | Without `--preflight` | **2** | Preflight confirmation required. |
| `manual_batch_execute_cache_write_requires_execute_live_http` | Without `--execute-live-http` | **2** | Live HTTP must be requested. |
| `manual_batch_execute_cache_write_requires_evaluate_cache_write` | Without `--evaluate-cache-write` | **2** | Refusal scaffold prerequisite required. |
| `manual_batch_smoke_live_http_not_confirmed` | `CONFIRM_US_LIVE_HTTP` or `CONFIRM_US_MANUAL_BATCH_SMOKE` not YES | **2** | Existing live/manual gates enforced. |
| `manual_batch_cache_write_requires_cache_gate` | `CONFIRM_US_CACHE_WRITE` not `YES` | **2** | Explicit operator cache gate. |
| `manual_batch_smoke_max_http_zero` | `--max-http` is 0 | **2** | Bounded cap required. |

Row-level safety (enforced by `stooq_live_preview_sanitized_bars` and `save_us_daily_bars_cache`):
`parse_error`, `transport_error`, `validation_error`, invalid-symbol, and capped rows never reach the writer; raw vendor response is never persisted; `STOOQ_APIKEY` is env-only and never in output.

---

## 7. Implementation checklist (R6.5.1–R6.5.7 all satisfied)

**R6.5.1 items (already satisfied):**

- [x] `docs/12`, `docs/13`, `docs/14`, `docs/15` aligned on R6.5.1 contract.
- [x] `--evaluate-cache-write` refusal scaffold implemented (exit 2 in all 6 orderings).
- [x] `monkeypatch save_us_daily_bars_cache` asserts it is never called (test coverage in R6.5.1).
- [x] Flag without `--live` refuses (exit 2, reason `manual_batch_cache_write_requires_live`).
- [x] `CONFIRM_US_CACHE_WRITE` not `YES` refuses (exit 2, reason `manual_batch_cache_write_requires_cache_gate`).
- [x] Full-gate path refuses with `manual_batch_cache_write_not_enabled_in_r6_5_1`.
- [x] `STOOQ_APIKEY` value never in output.
- [x] No `.github/` or `Makefile` wiring.
- [x] Existing R6.4.1 tests still pass without regression (459 tests total).

**R6.5.2 items (already satisfied):**

- [x] Tests planned and written before implementation (mock-first).
- [x] Test: `validation_error` live row refuses write.
- [x] Test: `parse_error` row refuses write.
- [x] Test: `transport_error` row refuses write.
- [x] Test: invalid symbol row refuses write.
- [x] Test: capped symbol (`max_http_cap_reached`) refuses write.
- [x] Test: success row classified eligible (observation only; no write performed).
- [x] Test: `save_us_daily_bars_cache` never called by eligibility classifier.
- [x] Test: raw body / raw CSV never in payload.
- [x] CI remains offline-safe.

**R6.5.3 items (already satisfied):**

- [x] `execute_manual_cache_write_for_eligible_rows` injected-writer candidate implemented.
- [x] Writer only called for `live_preview_ok` eligible rows; rejected rows never reach writer.
- [x] No real filesystem write in tests; writer is a fake callable.
- [x] No live HTTP consumed by write execution function.
- [x] 13 new mock-first tests (68 total).

**R6.5.4 items (already satisfied):**

- [x] `build_manual_cache_write_dry_run_plan` pure path-planning function implemented.
- [x] Target path deterministic: `outputs/market_data/us_daily_bars/{SYMBOL}.json`.
- [x] Unsafe symbols (path traversal, slash, etc.) rejected with `manual_batch_cache_write_rejects_unsafe_target_path`.
- [x] No file writes, no writer calls, no live HTTP — 11 new tests (84 total).

**R6.5.5 items (already satisfied):**

- [x] `execute_manual_cache_write_dry_run_plan_with_injected_writer` adapter contract implemented.
- [x] Accepts only dry-run plans; refuses invalid / non-dry-run / real-write-source inputs.
- [x] Writer invoked only for safe planned rows; rejected rows never reach writer.
- [x] `real_cache_write_performed` remains false; `writer_invoked` distinguishes injected-only invocation.
- [x] 14 new tests (98 total); no real FS write, no live HTTP, no CLI change.

**R6.5.6 items (already satisfied):**

- [x] `build_manual_cache_write_save_cache_writer_adapter` adapter boundary implemented.
- [x] Validates sanitized bars, symbol match, raw-response guard, API-key guard before calling injected save func.
- [x] 25 R6.5.6-labeled tests (126 total); no real FS write, no live HTTP, no CLI change.

**R6.5.7 items (already satisfied):**

- [x] `--execute-cache-write` CLI flag implemented; all 9 conditions required (5 flags + 3 env gates + `--max-http > 0`).
- [x] Requires `--live --preflight --execute-live-http --evaluate-cache-write --execute-cache-write` + `CONFIRM_US_LIVE_HTTP=YES` + `CONFIRM_US_MANUAL_BATCH_SMOKE=YES` + `CONFIRM_US_CACHE_WRITE=YES` + `--max-http > 0`.
- [x] Deterministic 7-step refusal ordering before production write executes.
- [x] Production write calls `stooq_live_preview_sanitized_bars(norm, live=True, write_cache=True)` which internally calls `save_us_daily_bars_cache`; no direct import of save func in batch smoke module.
- [x] `real_cache_write_performed: true` only when at least one row write succeeded.
- [x] `raw_response_included: false` and `provider_api_key_value_included: false` enforced.
- [x] No Makefile shortcut, no workflow wiring, no scheduler.
- [x] Tests use monkeypatched `stooq_live_preview_sanitized_bars`; no real filesystem write in CI.
- [x] 14 new R6.5.7-labeled tests (140 total, +14 from R6.5.6).

---

## 8. Required tests for R6.5.3+ implementation

R6.5.1 refusal scaffold tests (44) and R6.5.2 eligibility classifier tests (55 total) are implemented. These additional tests are required before R6.5.3 actual cache-write implementation may proceed:

- `test_cache_write_flag_without_live_exits_2`
- `test_cache_write_without_cache_gate_exits_2`
- `test_cache_write_validation_error_row_refused`
- `test_cache_write_parse_error_row_refused`
- `test_cache_write_transport_error_row_refused`
- `test_cache_write_invalid_symbol_row_refused`
- `test_cache_write_capped_symbol_row_refused`
- `test_cache_write_success_row_eligible_all_gates`
- `test_cache_write_calls_sanitized_writer_only`
- `test_cache_write_raw_body_not_in_payload`
- `test_cache_write_api_key_not_in_output`
- `test_cache_write_no_makefile_wiring`
- `test_cache_write_no_workflow_change`

---

## 9. Relationship to R6.6+ scheduled ingest

- **R6.5.x manual cache-write evaluation does not satisfy scheduled ingest readiness.**
- Successful R6.5.x runs are necessary learning for understanding write semantics, but are **not** sufficient approval for automation.
- **Scheduled ingest remains R6.6+** and requires all **`docs/13`** gates plus a future `CONFIRM_US_SCHEDULED_INGEST`-class milestone.
- No R6.5.x change should widen the scheduled ingest gate.

---

## 10. Document control

| Version | Milestone | Summary |
|---------|-----------|---------|
| **1.0** | **Main R6.5.0** | Design / checklist / refusal rules only — **no implementation**, **no cache write**, **no workflow change**. |
| **1.1** | **Main R6.5.1** | `--evaluate-cache-write` refusal scaffold implemented — **always refuses** (exit 2); **no cache write**, **no live HTTP**, **no raw response**; 11 new tests (44 total). |
| **1.2** | **Main R6.5.2** | `evaluate_manual_cache_write_eligibility_from_rows` pure classifier implemented — **no cache write**, **no live HTTP**, **no cache writer call**; 12 new tests (55 total, +11 from R6.5.1). |
| **1.3** | **Main R6.5.3** | `execute_manual_cache_write_for_eligible_rows` injected-writer execution candidate — **no real FS write in tests**, **no live HTTP**, **writer injected only**; 13 new tests (68 total); production-like write remains R6.5.4+. |
| **1.3.1** | **Main R6.5.3.1** | Clarify mock writer payload semantics — adds `writer_invoked` and `real_cache_write_performed: false` fields; `cache_write_performed` in mock path reflects injected writer exercised, **not** real FS persistence; 5 new tests (73 total). |
| **1.4** | **Main R6.5.4** | `build_manual_cache_write_dry_run_plan` — dry-run filesystem path validation only; **no file writes**, **no writer calls**, **no live HTTP**; 11 new tests (84 total); production-like write remains R6.5.5+. |
| **1.5** | **Main R6.5.5** | `execute_manual_cache_write_dry_run_plan_with_injected_writer` — injected-writer adapter contract; **no real FS write**, **no live HTTP**, **no CLI wiring**; 14 new tests (98 total); production-like real writer remains R6.5.6+. |
| **1.6** | **Main R6.5.6** | `build_manual_cache_write_save_cache_writer_adapter` — save-cache writer adapter boundary; **injected fake save-func only**; validates **all sanitized_bars rows** (symbol match, forbidden fields, non-dict); **no real FS write**, **no CLI wiring**; 25 R6.5.6-labeled tests (126 total); production-like CLI execution remains R6.5.7+. |
| **1.7** | **Main R6.5.7** | `--execute-cache-write` production CLI flag — all 9 conditions required; calls `stooq_live_preview_sanitized_bars(live=True, write_cache=True)`; `real_cache_write_performed: true` on success; **no Makefile / workflow wiring**; 14 new R6.5.7-labeled tests (140 total). |
| **1.7.1** | **Main R6.5.7.1** | Docs operator alignment — stale "actual write remains future" wording updated; §1/§5/§10 clarified; R6.5.7 manual write exists; scheduled ingest remains R6.6+; **docs-only, no src/tests/Makefile/workflow change**. |

---

## 11. R6.5.1 refusal ordering (implemented)

`--evaluate-cache-write` always returns `validation_error` (exit 2). Checks run in this order:

| Step | Missing condition | `reason` |
|------|-------------------|----------|
| 1 | `--live` not set | `manual_batch_cache_write_requires_live` |
| 2 | `--preflight` not set | `manual_batch_cache_write_requires_preflight` |
| 3 | `--execute-live-http` not set | `manual_batch_cache_write_requires_execute_live_http` |
| 4 | `CONFIRM_US_LIVE_HTTP` or `CONFIRM_US_MANUAL_BATCH_SMOKE` ≠ YES | `manual_batch_smoke_live_http_not_confirmed` |
| 5 | `CONFIRM_US_CACHE_WRITE` ≠ YES | `manual_batch_cache_write_requires_cache_gate` |
| 6 | All flags + all gates set | `manual_batch_cache_write_not_enabled_in_r6_5_1` (full-gate scaffold refusal) |

All 6 paths: `live_http_performed: false`, `cache_write_performed: false`, `raw_response_included: false`.
