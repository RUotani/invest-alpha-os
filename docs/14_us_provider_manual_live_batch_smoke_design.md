# US provider — operator-approved manual live batch smoke (**Main R6.2 design + R6.3 scaffold + R6.4.0 preflight**)

## 1. Purpose

**Main R6.2** anchored the **design** for **human-triggered, operator-approved, manual live batch smoke** — bounded **`--max-http`**, dual gates, **no** scheduler, **no** default cache write (**sections 2–8** below remain the contract).

**Main R6.3 adds (implemented — scaffold only):**

- **Module** **`src/invis_alpha_os/data/us_provider_manual_live_batch_smoke.py`**: **`build_us_provider_manual_live_batch_smoke_payload`**, **`render_manual_live_batch_smoke_markdown`**.
- **CLI** **`debug us-provider-manual-live-batch-smoke`** (**`--markdown`** optional): merges **`--from-watchlist`** + **`--symbols`** (same semantics as **`debug us-provider-scheduled-ingest-plan`**), applies **`--limit`** and **`--max-http`**, emits **`manual_live_batch_smoke_dry_run`** JSON or deterministic **`validation_error`** outcomes.
- **`--live`:** accepted for forward compatibility; **Main R6.3 never performs vendor HTTP** — real bounded GETs are **Main R6.4+**.
- **Optional Makefile:** **`make us-provider-manual-live-batch-smoke-dry-run`** — **no** **`--live`**, **no** **`--write-cache`**, not wired to **`verify`** / **`safe-push`**.

**Main R6.4.0 adds (implemented — preflight readiness only):**

- **`--preflight`** flag on **`debug us-provider-manual-live-batch-smoke`**: validates that all gates are set and **`--max-http > 0`** — emits **`manual_live_batch_smoke_preflight_ready`** (exit 0) or **`validation_error`** (exit 2).
- **Still zero vendor HTTP** and **zero cache writes** — preflight confirms readiness without executing.
- Plan rows change from **`dry_run_only`** / **`r6_3_scaffold_no_http_no_write`** to **`preflight_ready_no_http`** / **`r6_4_0_preflight_ready_no_http`**.
- **`operator_summary`** gains **`preflight_ready_count`**.
- **`next_required_approval`** updates to **`R6.4.1 manual live batch smoke execution`**.

Characteristics (unchanged from R6.2 intent):

| Attribute | Intended meaning |
|-----------|-------------------|
| **Manual** | A human runs **one CLI invocation** in an interactive / ops shell — **no** supervisor, **no** cron, **no** GitHub Actions **`schedule:`**. |
| **Operator-approved** | Distinct environment gates (section 5) attest intent **before** future **R6.4** HTTP consumes a budget. |
| **Batch smoke** | More than **one** symbol may be planned in **one** session under **`--max-http`** — **R6.3** reports **`planned_http_attempts`** only (**zero** wire I/O). |
| **Not production ingest** | No watchlist-wide automation; **R6.3** is observation / posture only. |
| **Not unattended automation** | **Scheduled ingest** stays **`docs/13`** **R6.6+** — **out of scope** here. |

Canonical neighbours:

- Phased roadmap: **`docs/13_us_provider_scheduled_ingest_design.md`**
- Failure matrix / playbook: **`docs/12_us_provider_failure_operator_playbook.md`**
- Provider plan: **`docs/11_us_market_data_provider_plan.md`**

---

## R6.3 scaffold — status / reason strings (JSON)

| `status` | `reason` | CLI exit | Notes |
|----------|----------|---------:|-------|
| **`manual_live_batch_smoke_dry_run`** | — | **0** | Default without **`--live`** or **`--preflight`**; **`live_http_performed`: false**. |
| **`validation_error`** | **`unsupported_provider`** | **2** | Only **`stooq_preview`**. |
| **`validation_error`** | **`empty_symbol_batch`** | **2** | No merged symbols. |
| **`validation_error`** | **`manual_batch_smoke_live_http_not_confirmed`** | **2** | **`--live`** / **`--preflight`** but missing **`CONFIRM_US_LIVE_HTTP=YES`** or **`CONFIRM_US_MANUAL_BATCH_SMOKE=YES`**. |
| **`validation_error`** | **`manual_batch_smoke_max_http_zero`** | **2** | **`--live`** with **`--max-http 0`**. |
| **`validation_error`** | **`manual_batch_smoke_live_execution_not_implemented_in_r6_3`** | **2** | **`--live`** (no **`--preflight`**) + both gates **`YES`** — **R6.4.1** executes HTTP. |

Envelope **`reason`** for valid plan rows (not top-level): **`r6_3_scaffold_no_http_no_write`** (dry-run) or **`r6_4_0_preflight_ready_no_http`** (preflight). Invalid symbols use **`invalid_symbol`** / **`excluded_invalid_symbol`**.

## R6.4.0 preflight — additional status / reason strings (JSON)

| `status` | `reason` | CLI exit | Notes |
|----------|----------|---------:|-------|
| **`manual_live_batch_smoke_preflight_ready`** | — | **0** | **`--preflight`** with both gates **`YES`** and **`--max-http > 0`**; **zero vendor HTTP**. |
| **`validation_error`** | **`manual_batch_smoke_live_http_not_confirmed`** | **2** | **`--preflight`** but gate(s) missing. |
| **`validation_error`** | **`manual_batch_smoke_max_http_zero`** | **2** | **`--preflight`** with both gates **`YES`** but **`--max-http 0`**. |

**Next milestone (success path after preflight):** **`next_required_approval`** string **`R6.4.1 manual live batch smoke execution`**.

---

## 2. Scope (design intent — R6.2 onward)

Future **R6.4** execution under this contract would extend the **R6.3** scaffold:

- **Manual operator command only** — same CLI name; **R6.3** already registers flags (**section “R6.3 scaffold”** above).
- **Small symbol batch** — **`--symbols`** and/or **`--from-watchlist`** + **`--limit`** (**implemented** in **R6.3** merge).
- **Explicit environment gate requirement** — **`CONFIRM_US_LIVE_HTTP=YES`** + **`CONFIRM_US_MANUAL_BATCH_SMOKE=YES`** before HTTP (**R6.4**).
- **Bounded max HTTP per run** — **`--max-http`** (**reported** in **R6.3** as **`planned_http_attempts`**).
- **No scheduler** — unchanged.
- **No automatic daily report insertion** — unchanged.
- **No production refresh** — unchanged.
- **No bulk cache write by default** — **R6.3** sets **`cache_write_allowed`: false** on rows; **no writer calls**.

---

## 3. Non-goals

The following remain **explicitly excluded** from **R6.3** (**and** from claiming **R6.4** until that milestone ships):

- **Real vendor HTTP** inside **R6.3** — **zero** GETs even when **`--live`** and gates are set.
- **Scheduled ingest execution**, **unattended live fetch**, **cron**, **GitHub Actions `schedule`** for this CLI path.
- **Automatic watchlist-wide refresh**, **production cache refresh**, **daily report auto-insertion**.
- **Portfolio-aware decision support** (**Main U** backlog).
- **Provider commercial finalization**, **yfinance fallback**, **Alpha Vantage live**, **metals / rates / macro** (**Main S** backlog).

---

## 4. CLI shape (**R6.3 implemented + R6.4.0 --preflight**)

```text
# R6.3 dry-run (no --live, no --preflight)
python -m invis_alpha_os.cli.main debug us-provider-manual-live-batch-smoke \
  --symbols MSFT,NVDA --provider stooq_preview --max-http 2

# R6.4.0 preflight readiness check (both gates must be set; zero HTTP)
CONFIRM_US_LIVE_HTTP=YES CONFIRM_US_MANUAL_BATCH_SMOKE=YES \
python -m invis_alpha_os.cli.main debug us-provider-manual-live-batch-smoke \
  --symbols MSFT,NVDA --provider stooq_preview --live --preflight --max-http 2
```

**Design notes:**

- Merge semantics mirror **`debug us-provider-cache-preview-batch`** and **`debug us-provider-scheduled-ingest-plan`** (**watchlist first**, CSV append, dedupe, **`limit`**).
- **`--max-http`:** non-negative; default **0**; **`planned_http_attempts = min(valid_symbol_count, max_http)`** (**R6.3** — informational; **R6.4.0** preflight also uses this cap).
- **`--live`:** **R6.3** (without **`--preflight`**) refuses execution. **R6.4.0**: combine **`--live --preflight`** to validate readiness (zero HTTP performed).
- **`--preflight`:** **R6.4.0** — gates check + max_http check → **`manual_live_batch_smoke_preflight_ready`** (exit 0) or **`validation_error`** (exit 2).

**Makefile:** **`make us-provider-manual-live-batch-smoke-dry-run`** (**`--max-http 0`**, no **`--live`**, no **`--preflight`**) — **`safe-push`** / **`verify`** / **`agent-final-check`** stay **independent** of this target.

---

## 5. Required gates (R6.4 execution — **not satisfied by R6.3 HTTP**)

Any **future R6.4** implementation **must** require:

| Requirement | Detail |
|-------------|--------|
| **`CONFIRM_US_LIVE_HTTP=YES`** | Same semantics as other US **`--live`** tooling (**`docs/12`**). |
| **`CONFIRM_US_MANUAL_BATCH_SMOKE=YES`** | Distinct gate (**R6.3** reads it for **`gate_status`** / refusal paths only). |
| **`CONFIRM_US_CACHE_WRITE`** (optional) | **Only** if an explicit cache-write sub-mode is added (**off** by default). |
| **`STOOQ_APIKEY`** | **Optional**, **environment-only** — **never** echoed (**R6.3** tests enforce). |

**R6.3:** if **`--live`** (no **`--preflight`**) and either gate is not **`YES`**, top-level **`reason`** is **`manual_batch_smoke_live_http_not_confirmed`** (**exit 2**) — **still zero HTTP**.

**R6.4.0:** if **`--preflight`** and either gate is not **`YES`**, same **`manual_batch_smoke_live_http_not_confirmed`** reason — **zero HTTP**. Both gates **`YES`** + **`--max-http > 0`** → **`manual_live_batch_smoke_preflight_ready`** (**exit 0**, zero HTTP).

---

## 6. Safety contract (JSON envelope posture)

| Flag | R6.3 scaffold posture | R6.4.0 preflight posture |
|------|------------------------|--------------------------|
| **`live_http_performed`** | **`false`** always. | **`false`** always. |
| **`cache_write_performed`** | **`false`** always. | **`false`** always. |
| **`raw_response_included`** | **`false`** always. | **`false`** always. |
| **`provider_api_key_value_included`** | **`false`** always. | **`false`** always. |
| **`scheduled_ingest_enabled`** | **`false`** always. | **`false`** always. |
| **`manual_batch_smoke_enabled`** | **`false`** (scaffold only). | **`false`** (preflight only). |
| **`preflight_requested`** | not present. | **`true`** when **`--preflight`** used. |
| **`requires_operator_approval`** | **`true`** (**constraints**). | **`true`** (**constraints**). |
| **`max_http_per_run`** / **`planned_http_attempts`** | From **`--max-http`** / **`min(valid_symbols, max_http)`**. | Same. |
| **`min_sleep_seconds`** | From env when set, else **`null`**. | Same. |

---

## 7. Failure handling (conceptual alignment with **`docs/12`**)

**R6.3** exposes scaffold-specific **`validation_error`** **`reason`** strings (see table in section 1). Operators should still triage Stooq **`results[]`** **`status` / `reason`** / **`body_kind`** via **`docs/12`** when **R6.4** adds live rows.

| Design bucket | **`docs/12`** alignment (when execution exists) |
|---------------|----------------------------------|
| **`validation_error`** | Scaffold gates / caps / empty batch (**R6.3** adds **`manual_batch_smoke_*`** reasons). |
| **`transport_error`** | **`http_error`** rows — **not emitted by R6.3** (no transport). |
| **`provider_api_key_required`** | Existing matrix (**not** reimplemented in **R6.3**). |
| **`parse_error`** | **R6.4+** vendor rows. |
| **`vendor_no_data`** | **R6.4+**. |
| **`success_sanitized_preview`** | **R6.4+**. |

---

## 8. Exit criteria before an implementation PR may claim “R6.4.1 execution live”

**Main R6.3** satisfies **scaffold / observation** tests. **Main R6.4.0** satisfies **preflight readiness** tests (**`tests/test_us_provider_manual_live_batch_smoke.py`** — 22 tests). **Main R6.4.1** (**real HTTP**) still requires:

1. **`docs/14`** + **`docs/13`** coherence for **R6.4.1** (**HTTP ON** when gates + **`--max-http > 0`** + **`--preflight`** passed first).
2. Automated proofs: **no HTTP** when gates missing; **`--max-http`** enforced on wire; **no** raw payload / API key values; **no** scheduler / workflow **`schedule:`** for this feature.

Tests **must not** use **`ALLOW_IMPORTANT=true`**.

---

## 9. Document control

| Version | Milestone | Notes |
|---------|-----------|--------|
| **1.0** | **Main R6.2** | Initial **manual live batch smoke design**. |
| **1.1** | **Main R6.3** | **Scaffold implemented** — CLI + module; **HTTP deferred** to **R6.4**. |
