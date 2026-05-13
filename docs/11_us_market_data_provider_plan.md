# US equities / ETFs — market data provider plan (Main R2–Main R6.1 plan renderer)

## 1. Purpose

This document selects and compares candidate **daily OHLCV** sources for the US watchlist path (`config/us_watchlist.yaml` → sanitized cache under `outputs/market_data/us_daily_bars/` → optional momentum renderer).

**Main R2 constraint:** **no live vendor HTTP**, **no API keys committed or printed**, **`raw_response` is never persisted** — only **design**, **YAML config**, and **dry-run URL/query previews** (`debug us-provider-preview`). All future ingest must funnel through **`save_us_daily_bars_cache`** after normalization to sanitized bar rows only. **Secrets** (including **`STOOQ_APIKEY`** if used) belong only in operator **environment** / local `.env` — never in committed YAML, git history, logs, or CLI JSON payloads.

Observation only — no buy/sell advice, no automated trading.

---

## 2. Candidate providers (summary)

### Alpha Vantage

- **Strengths:** Documented HTTPS API; **`TIME_SERIES_DAILY_ADJUSTED`** supports split/dividend-adjusted series; predictable JSON envelope for mapping.
- **Limitations:** **API key required**; **strict rate limits** (free tier usable for prototyping only); commercial use governed by Alpha Vantage terms.
- **ETFs / symbols:** Generally supports common tickers including **GOOGL**; **`BRK.B`**-style dots must be validated against Alpha Vantage’s symbol rules.

### Stooq

- **Strengths:** **Historical daily CSV-style** endpoint convenient for spreadsheets and prototyping; supports **Main R3** one-symbol **gated** shape-only live preview (see phased table).
- **Limitations:** **Not a formal “broker-grade” contractual API for production apps**; server responses may evolve — Stooq can answer **HTTP 200** with **non-tabular payloads** or prose indicating an **API key is required**. **Optional** gated live GET may append **`STOOQ_APIKEY`** from process environment only (**never committed, never logged, never in JSON previews** — keep keys in local `.env` / shell only). **Symbol convention risk** — US listings often encoded as **`{ticker}.us`** with hyphenation for multi-class dots (e.g. **BRK.B** → **`brk-b.us`** — heuristic in-repo); **not adjusted** in the same sense as vendor “adjusted close” products — treat field semantics carefully. **Treat as preview / prototype** until a commercial API path is chosen.
- **Operational:** Inspect **`validation_error`** / **`parse_error`** / **`http_error`** payloads using **`reason`**, **`status`**, and **`response_diagnostics`** per **`docs/12_us_provider_failure_operator_playbook.md`**. **Multi-symbol rollup:** **`debug us-provider-cache-preview-batch`** + **`run_stooq_cache_preview_batch`** (Main R5–**R5.3**) — **`operator_summary`** counts (**§3.2**) first; optional **`--markdown`** **copy-ready** recap (**§3.3**) — **still no raw body** in tooling output.

### Yahoo Finance / yfinance (unofficial)

- **Strengths:** Broad **ETF** and equity coverage; often includes **adjusted** columns in historical tables; easy local experimentation via `yfinance`.
- **Limitations:** **Unofficial / reverse-engineered** — **fragile** for automated production; **terms of use** restrict redistribution and non-personal use; **not** a stable “official API” contract. **Do not rely on fragile scraping** for core automation.

### Polygon / Tiingo (and similar paid APIs)

- **Strengths:** **Commercial APIs** with clearer licensing for apps; often strong **symbol resolution**, **adjusted** fields, and **rate plans** suitable for scale.
- **Limitations:** **Paid**; **API keys**; integration and compliance work per vendor; must still **never** write raw vendor JSON to cache — only sanitized OHLCV.

### Manual CSV / fixture-based import (in-repo today)

- **Strengths:** **No API key**; **fully reproducible** for CI and dry-runs; already implemented via **`debug us-daily-bars-cache-import`** and committed fixtures under `tests/fixtures/us_daily_bars/`.
- **Limitations:** Operator burden; not a substitute for automated refresh until a gated provider path exists.

---

## 3. Evaluation criteria

| Criterion | Notes |
|-----------|--------|
| **API key requirement** | Alpha Vantage / Polygon / Tiingo: yes. **Stooq:** may require an API key in practice for some deployments; gated tooling uses optional **`STOOQ_APIKEY`** (env-only) — see §2 Stooq. yfinance: no key but unofficial. |
| **Rate limits** | Alpha Vantage: tight on free tier. Paid vendors: plan-dependent. Stooq/yfinance: be conservative; no bulk hammering. |
| **Adjusted OHLC** | Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED`: yes. Yahoo tables often have adj. close. Stooq daily CSV: treat as **not** equivalent to a single “adjusted OHLCV” product without validation. |
| **ETF support** | Yahoo/yfinance typically broad; commercial APIs vary by listing; validate **GLDM**-class symbols per provider. |
| **Symbols (BRK.B / GOOGL)** | **Dots and class shares** differ per vendor — must maintain a **normalize → provider wire symbol** mapping table in a future ingest module; previews document best-effort heuristics only. |
| **Commercial / ToU** | Prefer providers with explicit API licenses for automated use; avoid violating Yahoo / scraping ToS for production automation. |
| **Reliability** | Official HTTPS APIs generally more stable than HTML or unofficial endpoints. |
| **Ease of cache integration** | All paths must converge on **`bars_from_rows`**-compatible sanitized JSON and **`save_us_daily_bars_cache`** — **never** **`raw_response`**. |

---

## 4. Phased approach

| Phase | Scope |
|-------|--------|
| **Main R2** | **Design** + **`config/us_market_data.yaml`** + **`build_us_provider_preview_plan`** / **`debug us-provider-preview`** — **no HTTP**, **no live ingestion**. |
| **Main R3** | **Stooq one-symbol gated live preview** — **`debug us-provider-live-preview`**: **`--live`** + **`CONFIRM_US_LIVE_HTTP=YES`**; **shape digest only** — **no cache write** — **no `raw_response`** (smoke symbol **MSFT**). |
| **Main R4 (current)** | **Stooq CSV strict parse → sanitized OHLCV dicts** (`parse_stooq_daily_csv_to_rows`) + **`stooq_live_preview_sanitized_bars`** / **`debug us-provider-cache-preview`**. **`--live`** gates HTTP; **`--write-cache`** + **`CONFIRM_US_CACHE_WRITE=YES`** gates **`save_us_daily_bars_cache`**. Vendor **raw CSV is never stored** on disk — only **sanitized** JSON via the existing writer. **One-symbol manual smoke**, **not** watchlist automation or scheduled refresh. **Stooq remains preview/prototype.** |
| **Main R4.1** | **Safe HTTP-200 diagnostics** — when gated Stooq fetch returns **`http_status` 200** but **strict CSV parse fails** (HTML page, terse “no data” text, wrong delimiter, unexpected header), **`parse_error`** payloads may include **`response_diagnostics`** from **`classify_stooq_csv_text_safely`**: capped header tokens, **`body_kind`**, delimiter guess — **never** vendor **raw bodies**, OHLC numeric cells, nor full lines. Helps operators distinguish “network OK” from “payload unusable”. |
| **Main R4.2** | **Stooq “API key required” (HTTP 200 prose)** — safe classification as **`response_diagnostics.body_kind: "api_key_required"`**; strict parse failures in that situation surface **`validation_error`** / **`reason: "provider_api_key_required"`** (exit **2**) instead of **`parse_error`**. Config: **`requires_api_key: true`**, **`api_key_env: "STOOQ_APIKEY"`**. Live GET merges env key into query **only when set** — **never** into committed YAML, previews, stderr, nor error payloads. **`build_stooq_daily_preview`** still lists **`apikey: "<redacted_required_later>"`** in **`query_params_without_secrets`** for operator visibility (**not** sent on wire unless replaced by **`STOOQ_APIKEY`**). |
| **Main R4.3** | **Failure matrix hardening** — **`classify_stooq_csv_text_safely`** adds **`delimiter_drift`** (heuristic delimiter mismatch vs data rows); API-key prose is detected from headers **or** bounded body (**overrides bare `html_like` when both apply**); **`html_like`** / terse **`no_data_like`** responses **omit** pseudo-header tokens derived from prose/HTML in **`response_diagnostics`** (**no markup words / vendor sentences** leaked). **`debug us-provider-*-preview`** returns stable **`parse_error`** reasons including **`stooq_payload_html_like`**, **`stooq_vendor_no_data`**, **`empty_csv`** (already used), **`stooq_csv_delimiter_drift`** where applicable; malformed CSV **`csv.reader`** failures attach diagnostics. **Still** gated one-symbol smoke only — **not** bulk/production refresh. |
| **Main R5** | **Multi-symbol cache preview design (no production refresh)** — **`debug us-provider-cache-preview-batch`** + **`run_stooq_cache_preview_batch`**: default **dry-run** (no HTTP); optional **`--live`** repeats **gated** **`stooq_live_preview_sanitized_bars`** per symbol (**still operator-triggered**, not scheduled). **Bulk cache write is rejected** at the batch envelope (**`batch_cache_write_not_supported`**); use single-symbol **`debug us-provider-cache-preview`** for writes. Emits **`batch_preview_ok`** with **`results[]`**, **`summary`** counts, **`operator_next_action`**, and **`cache_write_allowed`** per row (true only when a **single-symbol** follow-up write would be eligible). **`make us-provider-cache-preview-batch-dry-run`** (**`--limit`** small) is the default Makefile entry. |
| **Main R5.1** | **`operator_summary`** on the batch envelope — **operator triage buckets** (dry-run safe, single-symbol write candidates, API key needed, slug/mapping vs vendor-format classes, transport retry candidates, **`invalid_symbol_count`**, **`blocked_cache_write_count`**) derived from **`results[]`** (**integer counts only**, **no new HTTP**, **no bulk cache write**). **`docs/12`** §3.2 is canonical. **Pre‑R6:** operators must triage with **`operator_summary` + matrix** before proposing scheduled ingest. |
| **Main R5.2** | **`render_us_provider_cache_preview_batch_markdown`** + **`debug us-provider-cache-preview-batch --markdown`** — **counts / posture only** recap for operators (**no `results[]`**, **no disk write**, **still observation-only**). Prefer JSON export when diagnosing individual symbols. |
| **Main R5.3** | **Copy-ready Markdown layout** — blockquote (**JSON canonical**), **`## Operator verdict`**, **`## Safety flags`** table, summary tables, **`## Notes`** for paste into daily ops memos (**stdout only**; **no file write**, **no report automation**). |
| **Main R6.0** | **Scheduled ingest safety design only** — **`docs/13_us_provider_scheduled_ingest_design.md`**: phased roadmap (**R6.1–R6.4+**), gate proposals, ingest state machine (**no cron**, **no Actions schedule**, **no runtime ingest code**). |
| **Main R6.1** | **Dry-run scheduled ingest plan renderer** — **`us_provider_scheduled_ingest_plan.py`** + **`debug us-provider-scheduled-ingest-plan`**: emits **`scheduled_plan_dry_run`** (**symbol universe**, gates, constraints); **no HTTP**, **no cache write**, **no scheduler**. See **`docs/13`** §8. |
| **Beyond Main R6.1** | **R6.2+** unattended / batch execution per **`docs/13`** — Alpha Vantage / richer mapping remain separate commercial decisions; **nothing ships unattended** until **`CONFIRM_US_SCHEDULED_INGEST`** (future) and ops checklist pass. |

---

## 5. Default recommendation

1. Keep **manual file / fixture import** as the **fallback** forever (repro CI, outages, auditing).
2. For **automated** use, prefer a provider with an **explicit, stable HTTPS API** and acceptable **ToU for your use-case** (e.g. Alpha Vantage for prototyping; **Polygon/Tiingo-class** APIs for clearer commercial footing when budget allows).
3. **Avoid** coupling core automation solely to **unofficial Yahoo / HTML scraping**.
4. **Safety:** **No live HTTP by default.** **No API keys printed.** **`raw_response` never written.** All provider outputs must pass the **sanitized OHLCV cache writer** (`save_us_daily_bars_cache`) after validation.

For **failure triage**, use **`docs/12_us_provider_failure_operator_playbook.md`**. For **multi-symbol dry-run rollup**, **`make us-provider-cache-preview-batch-dry-run`**. For **scheduled ingest contract (design)**, **`docs/13_us_provider_scheduled_ingest_design.md`**. For **dry-run scheduled ingest plans** (symbol universe + gates, **no HTTP**), **`debug us-provider-scheduled-ingest-plan`**.
