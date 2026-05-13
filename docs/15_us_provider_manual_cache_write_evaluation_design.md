# US provider — manual cache-write evaluation safety design (**Main R6.5.0 design / R6.5.1 refusal scaffold**)

> **Document control:** v1.0 Main R6.5.0 (design only) → v1.1 Main R6.5.1 (refusal scaffold implemented).

## 1. Purpose

**Main R6.5.0** anchors the **safety design and checklist** for future **manual, operator-approved, bounded cache-write evaluation** — a potential follow-on to **R6.4.1 bounded live HTTP preview**.

**R6.5.0 is documentation only.**
- **No implementation** in R6.5.0.
- **No cache write** added.
- **No CLI flags** changed.
- **No workflow changes**.

**Main R6.5.1** implements `--evaluate-cache-write` as a **refusal scaffold only**.
- The flag is recognized and all 6 refusal orderings are deterministic (see §12 below).
- **No actual cache write** in R6.5.1.
- **No live HTTP consumed** by the `--evaluate-cache-write` path.
- **No raw response stored**, **no API key value in output**.
- Actual cache-write implementation remains **R6.5.2+** per the pre-implementation checklist.

Canonical neighbours:
- Live HTTP (R6.4.1): **`docs/14_us_provider_manual_live_batch_smoke_design.md`**
- Failure matrix / playbook: **`docs/12_us_provider_failure_operator_playbook.md`**
- Scheduled ingest (R6.6+): **`docs/13_us_provider_scheduled_ingest_design.md`**
- Provider plan: **`docs/11_us_market_data_provider_plan.md`**

---

## 2. Scope

Future **R6.5.1+** manual cache-write evaluation scope, when implemented:

- **Manual, bounded, operator-approved** — one CLI invocation; no supervisor, no cron, no GitHub Actions `schedule:`.
- **After successful live preview** — only rows that returned `live_preview_ok` in a preceding R6.4.1 run may be eligible for cache write.
- **Explicit flag required** — a dedicated future flag (proposed name `--evaluate-cache-write`; not yet in code) plus `CONFIRM_US_CACHE_WRITE=YES`.
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

Future **R6.5.1+** cache-write evaluation may only be attempted if **all** of the following are true:

| Requirement | Notes |
|-------------|-------|
| `--live` | Intent flag; already required for R6.4.1. |
| `--preflight` | Gate validation; already required for R6.4.1. |
| `--execute-live-http` | Live HTTP must have been requested. |
| Future explicit cache-write flag (proposed `--evaluate-cache-write`) | Dedicated intent; name may be finalized at implementation. |
| `CONFIRM_US_LIVE_HTTP=YES` | Same gate as R6.4.1. |
| `CONFIRM_US_MANUAL_BATCH_SMOKE=YES` | Same gate as R6.4.1. |
| `CONFIRM_US_CACHE_WRITE=YES` | Additional gate; currently read for `gate_status` only. |
| `--max-http > 0` | Bounded cap; same as R6.4.1. |
| Only `live_preview_ok` rows are eligible | `parse_error`, `transport_error`, `validation_error`, invalid, and capped rows are **never** eligible. |
| Sanitized bars only | Only bars passing the existing sanitized OHLCV writer validation may be written. |
| Raw vendor response is never written | Only sanitized row data reaches the cache writer. |
| API key value is never printed | `STOOQ_APIKEY` remains env-only. |
| Cache target is deterministic and under `outputs/market_data/us_daily_bars/` only | No arbitrary paths. |
| Never from CI / workflow / Makefile shortcut | Manual operator invocation only. |

---

## 5. Proposed future CLI shape (**documentation only — not implemented**)

```text
# Proposed — not implemented in R6.5.0
python -m invis_alpha_os.cli.main debug us-provider-manual-live-batch-smoke \
  --symbols MSFT \
  --provider stooq_preview \
  --live \
  --preflight \
  --execute-live-http \
  --evaluate-cache-write \
  --max-http 1
```

`--evaluate-cache-write` is **proposed only**. The actual flag name may be finalized at implementation. Do not use this shape until R6.5.1 ships.

---

## 6. Refusal rules — proposed reason strings (**proposed / not implemented in R6.5.0**)

| Proposed reason string | Trigger | Expected exit | Safety intent |
|------------------------|---------|:-------------:|---------------|
| `manual_batch_cache_write_not_implemented_in_r6_5_0` | Cache-write flag used before implementation ships | **2** | Scaffold refusal; prevents premature use. |
| `manual_batch_cache_write_requires_live` | `--evaluate-cache-write` without `--live` | **2** | Live intent required. |
| `manual_batch_cache_write_requires_preflight` | Without `--preflight` | **2** | Preflight confirmation required. |
| `manual_batch_cache_write_requires_execute_live_http` | Without `--execute-live-http` | **2** | Live HTTP must be requested. |
| `manual_batch_cache_write_requires_cache_gate` | `CONFIRM_US_CACHE_WRITE` not `YES` | **2** | Explicit operator gate. |
| `manual_batch_cache_write_requires_successful_live_preview` | No `live_preview_ok` rows | **2** | Only successful previews eligible. |
| `manual_batch_cache_write_rejects_invalid_symbol` | Row reason `invalid_symbol` | row-level | Invalid symbols never written. |
| `manual_batch_cache_write_rejects_parse_error` | Row status `parse_error` | row-level | Corrupt data never written. |
| `manual_batch_cache_write_rejects_transport_error` | Row status `transport_error` | row-level | Transport failures never written. |
| `manual_batch_cache_write_rejects_validation_error` | Row status `validation_error` | row-level | Validation failures never written. |
| `manual_batch_cache_write_rejects_max_http_capped_row` | Row reason `max_http_cap_reached` | row-level | Unattempted rows never written. |
| `manual_batch_cache_write_rejects_raw_response` | Any attempt to write raw body | blocked | Raw vendor content never persisted. |
| `manual_batch_cache_write_rejects_automation_context` | Invoked from CI / workflow | **2** | Manual operator only. |

---

## 7. Checklist before R6.5.1 implementation may start

- [ ] `docs/12`, `docs/13`, `docs/14`, `docs/15` aligned on R6.5.1 contract.
- [ ] Tests planned and written **before** implementation (mock-first).
- [ ] `monkeypatch save_us_daily_bars_cache` asserts it is never called when gates missing.
- [ ] Test: proposed flag without `--live` refuses (exit 2, reason `manual_batch_cache_write_requires_live`).
- [ ] Test: `CONFIRM_US_CACHE_WRITE` not `YES` refuses (exit 2, reason `manual_batch_cache_write_requires_cache_gate`).
- [ ] Test: `validation_error` live row refuses write.
- [ ] Test: `parse_error` row refuses write.
- [ ] Test: `transport_error` row refuses write.
- [ ] Test: invalid symbol row refuses write.
- [ ] Test: capped symbol (`max_http_cap_reached`) refuses write.
- [ ] Test: success row only write-eligible when all gates pass.
- [ ] Test: `save_us_daily_bars_cache` called only with sanitized bars when all gates pass.
- [ ] Test: raw body / raw CSV never in payload or Markdown.
- [ ] Test: `STOOQ_APIKEY` value never in output.
- [ ] Confirm no `.github/` or `Makefile` wiring.
- [ ] Confirm CI remains offline-safe.
- [ ] Confirm write target path is deterministic and under `outputs/market_data/us_daily_bars/`.
- [ ] Existing R6.4.1 tests still pass without regression.

---

## 8. Required tests for future implementation

Expected tests only — **do not implement until R6.5.1 milestone begins**:

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
| **1.1** | **Main R6.5.1** | `--evaluate-cache-write` refusal scaffold implemented — **always refuses** (exit 2); **no cache write**, **no live HTTP**, **no raw response**; 11 new tests (44 total); actual write remains R6.5.2+. |

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
