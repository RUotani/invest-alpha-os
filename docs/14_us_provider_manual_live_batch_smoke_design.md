# US provider — operator-approved manual live batch smoke (**Main R6.2 design-only**)

## 1. Purpose

**Main R6.2** (this document) defines the **design** for the next incremental milestone **after [`docs/13_us_provider_scheduled_ingest_design.md`](13_us_provider_scheduled_ingest_design.md) R6.1**: **human-triggered, operator-approved, manual live batch smoke** against a **small bounded set** of normalized symbols.

**R6.2 is design-only in this milestone.** There is **no implementation** obligation in the same revision as adopting this doc.

Characteristics:

| Attribute | Intended meaning |
|-----------|-------------------|
| **Manual** | A human runs **one CLI invocation** in an interactive / ops shell — **no** supervisor, **no** cron, **no** GitHub Actions **`schedule:`**. |
| **Operator-approved** | Distinct environment gates (section 5) attest that the operator **intentionally** enabled bounded live HTTP for this run. |
| **Batch smoke** | More than **one** symbol may be exercised in **one** deliberate session, under **explicit caps** (e.g. **`max_http`**), still **observation-first** — **not** “production ingest”. |
| **Not production ingest** | No watchlist-wide automatic refresh; no unattended loop; outputs are **for validation / ops confidence**, aligned with **`docs/12`** triage posture. |
| **Not unattended automation** | **Scheduled ingest execution** remains **`docs/13`** **R6.4+** and requires future **`CONFIRM_US_SCHEDULED_INGEST`**-class gates — **out of scope** for R6.2. |

Canonical neighbours:

- Phased ingest roadmap (**R6.0–R6.4+**): **`docs/13`**
- Failure matrix / operator playbook (**implemented today**): **`docs/12`**
- Provider plan / phased history: **`docs/11`**

---

## 2. Scope (design intent)

Future implementation under this contract would include:

- **Manual operator command only** — a single **`debug`** subcommand (proposed section 4) run by a human when needed.
- **Small symbol batch** — explicit **`--symbols`** and/or **`--from-watchlist`** + **`--limit`**; **normalized** universe only; duplicates removed.
- **Explicit environment gate requirement** — at minimum **`CONFIRM_US_LIVE_HTTP=YES`** and **`CONFIRM_US_MANUAL_BATCH_SMOKE=YES`** before any vendor GET (section 5).
- **Bounded max HTTP per run** — CLI flag such as **`--max-http N`** (**N** small, enforced); must **never** exceed the planned cap regardless of symbol list length.
- **No scheduler** — no process manager tick, cron, Actions schedule, or “daily job” semantics.
- **No automatic daily report insertion** — no wiring into **`daily`** / report generators as a side effect of this CLI.
- **No production refresh** — not a substitute for an approved ingest pipeline or commercial API contract.
- **No bulk cache write by default** — default posture: **sanitized previews / shape-aligned outcomes only** (same hygienic envelopes as **`docs/12`**); any optional future **explicit** cache-write mode would be **separate**, **dual-gated**, and **documented independently** (section 5).

---

## 3. Non-goals

The following remain **explicitly excluded** from R6.2 (design and any future implementation that claims the R6.2 name):

- **Scheduled ingest execution** — unattended loops, supervisor-driven refresh.
- **Unattended live fetch** — any HTTP **without** a human at the keyboard and section 5 gates.
- **Cron** — host-level timers.
- **GitHub Actions `schedule`** (or equivalent CI timers) for vendor fetch.
- **Automatic watchlist-wide refresh** — no “sync entire watchlist” automation.
- **Production cache refresh** — no implication of SLA-backed freshness.
- **Daily report auto-insertion** — no coupling to **`pack`**, **`daily`**, or templated Markdown emitters beyond what operators manually paste today.
- **Portfolio-aware decision support** — (**Main U** backlog).
- **Provider commercial selection finalization** — Stooq remains **preview / prototype** tier until a separate programme decides otherwise (**`docs/11`**).
- **yfinance fallback** — scraping / unofficial paths are **not** in scope.
- **Alpha Vantage live implementation** — no new vendor HTTP surface in this milestone family.
- **Metals / rates / macro integration** — **Main S** scope.

---

## 4. Proposed future CLI shape (**documentation only — not implemented**)

Examples illustrate **intent** only. Exact flag names may change during implementation PRs **after this design is accepted**.

```text
python -m invis_alpha_os.cli.main debug us-provider-manual-live-batch-smoke \
  --symbols MSFT,NVDA --provider stooq_preview --max-http 2

python -m invis_alpha_os.cli.main debug us-provider-manual-live-batch-smoke \
  --from-watchlist --provider stooq_preview --limit 3 --max-http 3
```

**Design notes:**

- Merge semantics for **`--from-watchlist`** + **`--symbols`** should mirror **`debug us-provider-cache-preview-batch`** and **`debug us-provider-scheduled-ingest-plan`** (**watchlist first**, then appended CLI symbols; dedupe; then **`limit`** if present).
- **`--max-http`** caps **successful or attempted** GET budget per invocation (exact counting rules TBD at implementation — must be conservative and operator-visible in JSON envelope).
- **No `--live` alias games** — the command either **requires** gates or exits **`validation_error`**; “forgetting gates” must **never** silently perform HTTP (section 8).

**No Makefile target is prescribed** until implementation; **`safe-push`** / **`verify`** / **`ai-check`** / **`agent-final-check`** must **not** depend on this CLI.

---

## 5. Required gates (future implementation)

Any future **`us-provider-manual-live-batch-smoke`** implementation **must**:

| Requirement | Detail |
|-------------|--------|
| **`CONFIRM_US_LIVE_HTTP=YES`** | Same human gate semantics as **`debug us-provider-cache-preview-batch --live`** today (**`docs/12`**). |
| **`CONFIRM_US_MANUAL_BATCH_SMOKE=YES`** | **New** distinct gate — documents that this session is intentional **manual batch smoke**, not accidental reuse of single-symbol tooling. |
| **`CONFIRM_US_CACHE_WRITE`** (optional) | **Only** if an **explicit**, **separate** cache-write mode is added later (**off by default**). Any write path still requires **`CONFIRM_US_CACHE_WRITE=YES`** and must **never** imply bulk unattended semantics. |
| **`STOOQ_APIKEY`** | **Optional**, **environment-only**, same posture as **`docs/11`** / **`docs/12`** / **`docs/13`** — **never** echoed in stdout, stderr, Markdown, commits, or tests. |

If **either** **`CONFIRM_US_LIVE_HTTP`** or **`CONFIRM_US_MANUAL_BATCH_SMOKE`** is not exactly **`YES`**, the tooling **must refuse** HTTP with **`validation_error`** / matrix-aligned **`live_http_not_confirmed`** family reasons (exact **`reason`** string TBD at implementation — must be deterministic and test-stable).

---

## 6. Safety contract (planned JSON envelope posture)

Design-level flags for observability (**not** a committed schema yet):

| Flag | Planned R6.2 manual batch smoke posture |
|------|----------------------------------------|
| **`live_http_performed`** | **`true`** **only when** section 5 gates satisfied **and** at least **one** bounded GET attempted; **`false`** on refusal paths. |
| **`cache_write_performed`** | **`false`** **by default**; **`true`** only under an **explicit optional** write mode + **`CONFIRM_US_CACHE_WRITE=YES`** (if ever added — **still not bulk automation**). |
| **`raw_response_included`** | **`false`** always — vendor bodies **never** in JSON / Markdown tooling output (**`docs/12`** invariant). |
| **`provider_api_key_value_included`** | **`false`** always — only env **names** may appear where already established (e.g. **`STOOQ_APIKEY`**). |
| **`scheduled_ingest_enabled`** | **`false`** always — this CLI **never** arms scheduling. |
| **`requires_operator_approval`** | **`true`** — dual gate section 5 is mandatory precedent to HTTP budget consumption. |
| **`max_http_per_run`** | **Positive integer**, from CLI (`--max-http`) capped by safer internal ceiling (**TBD**); must mirror actual attempts + refusals policy in docs at implementation time. |
| **`min_sleep_seconds`** | **`null`** or **non‑negative float** — if set (env or CLI), honoured between successive GETs for politeness (align with **`docs/13`** section 4.2 **`US_PROVIDER_MIN_SLEEP_SECONDS`** when applicable). |

---

## 7. Failure handling (conceptual alignment with **`docs/12`**)

Implementation **must** classify outcomes using the **existing Stooq preview failure vocabulary** (**`docs/12`** **`status`** / **`reason`** / **`response_diagnostics.body_kind`**) so operators do not learn a second matrix.

Design-level buckets (map to **`docs/12`** rows — names below are **conceptual** labels for this document):

| Design bucket | **`docs/12`** alignment (today) |
|---------------|----------------------------------|
| **`validation_error`** | Gates, invalid symbols, unsupported provider, empty batch, caps exceeded before HTTP, etc. |
| **`transport_error`** | **`http_error`** **`status`** paths — **`network_or_timeout`**, **`http_status_*`**, **`http_error`** (**`docs/12`** section 3 **`transport`** group). |
| **`provider_api_key_required`** | **`validation_error`** + **`reason == provider_api_key_required`** (**`body_kind`** **`api_key_required`** where applicable). |
| **`parse_error`** | **`parse_error`** **`status`** rows — **`stooq_*`**, **`csv_*`** reasons with **`response_diagnostics`** only (**no raw body**). |
| **`vendor_no_data`** | Primarily **`stooq_vendor_no_data`** (**`body_kind`** **`no_data_like`**) plus related empty / no-rows classes per matrix. |
| **`success_sanitized_preview`** | **`preview_ok`** / **`live_preview_ok`** (**shape / strict parse**) — **still not** implying production ingest or unattended refresh. |

**Per-symbol rows** remain canonical for diagnostics; optional **future** envelope-level **`operator_summary`**-style rollup should **reuse** **`docs/12`** buckets rather than inventing parallel taxonomies.

---

## 8. Exit criteria before an implementation PR may claim “R6.2 implemented”

**This design acceptance** (`docs/14` reviewed **as documentation**) is **necessary but not sufficient** for code. Implementation may only bear the label **after**:

1. **This document** (**`docs/14`**) + **`docs/13`** phased roadmap + **`docs/12`** matrix coherence are acknowledged by maintainers (**paper sign-off**, no automation).
2. **Automated tests** prove at least (**non-exhaustive minimum bar**):

   - **No live HTTP** unless **both** **`CONFIRM_US_LIVE_HTTP=YES`** **and** **`CONFIRM_US_MANUAL_BATCH_SMOKE=YES`** are set (mock transport; assert **zero** `urllib` / HTTP client calls when gates missing).
   - **No cache write** in default code paths (assert writer not invoked unless **explicit** future write mode exists **and** **`CONFIRM_US_CACHE_WRITE`** gate engages).
   - **`--max-http` (or equivalent) cap enforced** — attempts **cannot** exceed declared budget (table-driven tests with mocks).
   - **Raw vendor payload** is **never** stored on disk nor printed to stdout (**snapshot / mock** proofs).
   - **API key value** is **never** printed or embedded in payloads (regex / negative tests mirroring **`docs/12`** policy tests where applicable).
   - **No scheduler / workflow schedule added** — `grep`/CI/assertions confirm **no** cron examples, **no** **`schedule:`** YAML in workflows for vendor fetch attributable to this feature.

Tests **must not** use **`ALLOW_IMPORTANT=true`** as a workaround for safe-push hygiene.

---

## 9. Document control

| Version | Milestone | Notes |
|---------|-----------|--------|
| **1.0** | **Main R6.2** | Initial **manual live batch smoke design** — **implementation explicitly deferred**. |
