# Investment OS coverage map (Main Q0)

## 1. Purpose

This document is the repository-level **coverage map and progress baseline** for the intended **Investment OS** programme.  
Progress percentages attached to past workstreams often reflected the **Japan equity / J-Quants / Momentum Score v2** subsystem only. Here we separate:

- **subsystem progress** (narrow, implementable slices), and  
- **total Investment OS progress** (full multi-asset, reporting, holdings, and decision-support scope).

Going forward, **never report a single percentage without naming the scope**. Use at least:

- subsystem progress (named),
- total Investment OS progress (this document),
- asset-class coverage (which rows below are advancing).

**Observation-only posture:** documentation and planning—no execution of trades, no buy/sell advice, no automated trading, no market data fetch in this file.

---

## 2. Current baseline summary

| Lens | Approximate progress | Notes |
|------|----------------------|-------|
| **JP equities momentum pipeline subsystem** (sanitized OHLCV cache → Momentum Score v2 → daily section → observations → Action Watchlist for cache-only rows) | **about 80–85%** | **Not** broader JP equity research (fundamentals / earnings models / intrinsic valuation remain unintegrated here); strongest *technical OHLCV* vertical in-repo |
| **Total Investment OS** (all rows in §3 treated as one programme) | **about 45%** (tiny bump after Main R5 **batch preview tooling** — still **observer / manual gates only**) | Early outside JP OHLCV + reporting; Main R4 adds **optional** gated vendor→cache for **one US symbol**; Main R5 adds **`debug us-provider-cache-preview-batch`** / **`make us-provider-cache-preview-batch-dry-run`** for **multi-symbol summarized preview** (**no bulk cache write**, **no unattended live HTTP**) |

These numbers are **judgment calls for planning**, not audited metrics.

---

## 3. Scope table

Status legend (short): **N/S** not started · **Conc** conceptual / backlog · **Partial** early integration · **Active** recurring use in-repo.

Progress % is directional (same caveat as §2).

| Area | Implementation status | Progress % | Data source status | Signal status | Report status | Next priority |
|------|-------------------------|------------|--------------------|--------------|---------------|---------------|
| **JP equities / J-Quants** | Cache-backed daily bars → signals → daily Markdown | ~80–85% | Active (local sanitized JSON cache; optional live ingest behind gates elsewhere) | Momentum Score v2 + CLI | Daily section + Observations + Action Watchlist (cache-only) | Liquidity/context fields, QA on edge cases |
| **US equities** | Through **Main R4–R5**: **Stooq strict CSV parse → sanitized bars**; **optional gated cache write** via **`debug us-provider-cache-preview`** (single-symbol only); **Main R5** **`debug us-provider-cache-preview-batch`** merges watchlist / CLI symbols into **`results[]`** + **`summary`** (**default dry-run**, **batch refuses `--write-cache`**); shape-only **`debug us-provider-live-preview`** (Main R3). Optional **`STOOQ_APIKEY`** (env-only). **No bulk cache writer**, **no bulk watchlist live fetch** by automation. | **~25–30%** | **Operator-gated** Stooq smoke (single- or multi-symbol CLI); **`data fetching still not implemented`** for **automated** production-wide refresh | Momentum-ready when cache populated | Hidden from daily unless `include_us_momentum_cache_only_section` | Scheduling / unattended multi-symbol ingest beyond manual CLI |
| **US ETFs** | Same tray; Stooq `*.us` may work per listing (**symbol-specific validation**) | **~25–30%** | Fixture / import + same gated framing as equities — **bulk production refresh**: **data fetching still not implemented** | As above | As above | Bundled under **Main R** slice |
| **gold / silver / copper / metals** | Not started | ~0–5% | None in-repo | None | None | **Main S**: commodity / macro-adjacent design |
| **bonds / rates** | Not started | ~0–5% | None in-repo | None | None | **Main S** |
| **crypto proxies** (e.g. MSTR / COIN / MARA narrative scope) | **US watchlist** (`crypto_proxy` group); no quote ingest | ~5–15% | None in-repo | None | None | Main R1+ data path |
| **macro regime** | Ideas / governance docs partially | ~10–20% | Not wired to ingestion | Not integrated | Mentioned conceptually | **Main S**: explicit macro inputs & regime taxonomy |
| **portfolio holdings / allocation** | Evidence/outcome scaffolding exists; holdings light | ~10–20% | Manual / fragmented | Minimal | Partial (observation ethos) | **Main T**: holdings ingestion + drift vs policy |
| **daily report / action layer** | Strong for JP momentum; scoped observation-only actions | ~40–50% JP slice; ~15–25% global | Depends on pillar | Mirrors data above | JP momentum rich | Extend only with real data feeds per pillar |
| **automation / ops / CI** | Makefile, safe-push gates, jq workflows | ~50–60% ops for current scope | N/A | N/A | N/A | Harden docs + cross-pillar reproducibility |

---

## 4. Capability maturity model

Use these stages to compare pillars without implying production readiness:

| Stage | Meaning |
|-------|---------|
| **0** | Not started |
| **1** | Concept / watchlist only |
| **2** | Data acquisition (planned or ad hoc) |
| **3** | Cache / normalization |
| **4** | Signal generation |
| **5** | Daily report |
| **6** | Action watchlist (observation / next-check cues, not trades) |
| **7** | Portfolio-aware decision support |
| **8** | Automated monitoring with safety gates |

---

## 5. Current module status (explicit)

- **JP equities**: approximately **stage 5–6** today (Momentum daily report plus Action Watchlist on cache-backed rows — observation only).
- **Main R (this milestone)**: added **`config/us_watchlist.yaml`**, **`us_watchlist` / `us_daily_bars_cache`** modules, optional **gated** `render_us_momentum_cache_only_section`, and **`us-watchlist-preview`** — watchlist + on-disk contract + tests.
- **Main R1**: committed **`tests/fixtures/us_daily_bars/`** OHLCV JSON, **`debug us-daily-bars-cache-import`**, **`make us-cache-fixture-import`**, **`make us-momentum-check`** — **fixture-only cache population** until provider ingest lands.
- **Main R2**: **`docs/11_us_market_data_provider_plan.md`**, **`config/us_market_data.yaml`**, **`us_provider_preview`**, **`debug us-provider-preview`**, **`make us-provider-preview`** — **dry-run preview only** (**no HTTP**, **no `raw_response`**, **vendor fetch not implemented**).
- **Main R3**: **`debug us-provider-live-preview`**, **`make us-provider-live-preview-dry-run`** — gated **shape-only** Stooq preview (**no cache write**).
- **Main R4**: **`us_stooq_daily_csv`**, **`stooq_live_preview_sanitized_bars`**, **`debug us-provider-cache-preview`**, **`make us-provider-cache-preview-dry-run`** — strict **CSV → sanitized OHLC**; optional **`save_us_daily_bars_cache`** when **`CONFIRM_US_CACHE_WRITE=YES`** **and** **`--write-cache`**; vendor **CSV never stored**.
- **Main R4.1**: **`classify_stooq_csv_text_safely`** — on **`parse_error`** from strict Stooq parse, attaches **`response_diagnostics`** (**no raw body / no OHLC cells**) when **HTTP succeeds** but payload is HTML, terse no-data prose, delimiter drift, etc.
- **Main R4.2**: Stooq may return HTTP **200** with **API-key-required prose** — classified safely as **`body_kind: "api_key_required"`**; surfaced as **`validation_error`** / **`provider_api_key_required`** (not **`parse_error`**). **`STOOQ_APIKEY`** is optional, **env-only** for gated live GET; never committed or echoed in tooling output.
- **Main R4.3**: Stooq tooling **failure matrix** — stable **`parse_error`** / **`reason`** values (e.g. **`stooq_payload_html_like`**, **`stooq_vendor_no_data`**, **`stooq_csv_delimiter_drift`**) keyed off **`response_diagnostics.body_kind`** (**`delimiter_drift`**, plus existing **`csv_like`/`empty`/…**) with **sanitized diagnostics only**; HTML / no-data responses do not echo vendor prose/markup tokens in **`header_columns_sanitized`**.
- **Main R4.4**: **US provider operator playbook** — **`docs/12_us_provider_failure_operator_playbook.md`** documents the **failure matrix** (`status` / `reason` / `body_kind`), **safe vs forbidden** handling (**no new live ingestion** added in R4.4 alone).
- **Main R5**: **`run_stooq_cache_preview_batch`** in **`src/invis_alpha_os/data/us_provider_cache_preview_batch.py`**; **`debug us-provider-cache-preview-batch`** + **`make us-provider-cache-preview-batch-dry-run`** — **multi-symbol** JSON rollup (**`batch_preview_ok`**, per-row statuses, **`summary`** counts aligning with §3 matrix / transport bucket); **explicitly rejects** batch **`--write-cache`**; **`raw_response_included: false`**; **gates unchanged** (**`CONFIRM_US_LIVE_HTTP`** for **`--live`**).
- **Main R5.1**: **`operator_summary`** (**`compute_operator_summary_from_rows`**) on the same batch envelope — failure-matrix–aligned **integer triage buckets** for watchlist-scale human review (**still no unattended HTTP**, **no bulk cache writes**); see **`docs/12`** §3.2 and **pre‑R6** gate wording in **`docs/12`** §5.
- **Main R5.2**: **`render_us_provider_cache_preview_batch_markdown`** + CLI **`--markdown`** — operator **Markdown recap** (**summary / operator_summary**; **omits `results[]`**); **no new fetch**, **no cache persistence**; see **`docs/12`** §3.3.
- **Main R5.3**: **Copy-ready stdout ordering** — verdict + safety-flag table + notes tuned for manual paste (**still JSON canonical** for rows).
- **Main R6.0**: **`docs/13_us_provider_scheduled_ingest_design.md`** — scheduled / unattended ingest **safety contract** (**design-only**; **no cron**, **no Actions schedule**, **no new HTTP/cache code**).
- **Main R6.1**: **`build_us_provider_scheduled_ingest_plan`** / **`debug us-provider-scheduled-ingest-plan`** — **`scheduled_plan_dry_run`** JSON / Markdown (**watchlist + CLI symbol merge**); **no HTTP**, **no cache write**, **no scheduler** — see **`docs/13`** §8.
- **US equities / ETFs / listed crypto proxies**: configuration **stage ~2**; sanitized US cache **stage ~3** after manual fixture, **fixture import**, or **operator-triggered gated Stooq write** — still **no** unattended multi-symbol refresh pipeline.
- **Metals**, **rates** (non-proxy): unchanged backlog until **Main S**.
- **Macro regime**: conceptual and doc-level; **not fully integrated** as a repeatable data + signal pipe in-repo.
- **Portfolio-aware decision support**: **still early** (aligns roughly with stages **1–3** depending on subsystem).

---

## 6. Recommended next sequence

After Main Q / Q0:

| Phase | Theme |
|-------|--------|
| **Main R4** | **Stooq parse + optional gated one-symbol vendor cache write** — **automated bulk refresh remains future work** |
| **Main R5** | **Multi-symbol US provider cache preview batch** (**dry-run default**, **observer JSON**, **no bulk cache writes**) |
| **Main R5.1** | **`operator_summary`** buckets + **pre‑R6 human triage discipline** (**docs/11–12**) — **not** ingest automation |
| **Main R5.2** | **`--markdown` operator recap** (**counts only**) — **not** row-level JSON, **not** automated refresh |
| **Main R5.3** | **Copy-ready Markdown section order** — **stdout paste helper only** |
| **Main R6.0** | **`docs/13`** scheduled ingest **safety design** — **no automation** |
| **Main R6.1** | **Dry-run scheduled ingest plan renderer** — JSON / Markdown posture only (**`docs/13`** §8) |
| **Main R6+** | Scheduled / unattended watchlist ingest execution, additional commercial providers (**only after `docs/13` gates + explicit implementation milestones**, **post‑R6.1**) |
| **Main S** | Metals / macro / rates source design |
| **Main T** | Portfolio holdings ingestion / allocation gap |
| **Main U** | Cross-asset decision dashboard |

Order can shift if compliance or availability constraints surface; treat this as **default sequencing**, not a contract.

---

## 7. Progress reporting rule

Any future Executive summary or changelog that cites a **progress %** must include **all three**:

1. **subsystem progress** (name the subsystem, e.g. “JP equities momentum”).
2. **total Investment OS progress** (explicitly labelled – see §2).
3. **asset-class coverage** (which scope-table rows moved, even if unchanged).

Avoid publishing an isolated headline number.

---

### Quick reference wording (copy-paste)

- **subsystem progress**: _Named slice of the roadmap (narrow scope)._  
- **total Investment OS progress**: _Breadth-weighted judgment across §3._

These phrases are deliberate keywords for tooling and audits.
