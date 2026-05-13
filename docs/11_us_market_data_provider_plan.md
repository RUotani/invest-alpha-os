# US equities / ETFs — market data provider plan (Main R2)

## 1. Purpose

This document selects and compares candidate **daily OHLCV** sources for the US watchlist path (`config/us_watchlist.yaml` → sanitized cache under `outputs/market_data/us_daily_bars/` → optional momentum renderer).

**Main R2 constraint:** **no live vendor HTTP**, **no API keys committed or printed**, **`raw_response` is never persisted** — only **design**, **YAML config**, and **dry-run URL/query previews** (`debug us-provider-preview`). All future ingest must funnel through **`save_us_daily_bars_cache`** after normalization to sanitized bar rows only.

Observation only — no buy/sell advice, no automated trading.

---

## 2. Candidate providers (summary)

### Alpha Vantage

- **Strengths:** Documented HTTPS API; **`TIME_SERIES_DAILY_ADJUSTED`** supports split/dividend-adjusted series; predictable JSON envelope for mapping.
- **Limitations:** **API key required**; **strict rate limits** (free tier usable for prototyping only); commercial use governed by Alpha Vantage terms.
- **ETFs / symbols:** Generally supports common tickers including **GOOGL**; **`BRK.B`**-style dots must be validated against Alpha Vantage’s symbol rules.

### Stooq

- **Strengths:** **No API key** for public CSV-style daily endpoints; convenient for sketches and spreadsheets.
- **Limitations:** **Not a formal “broker-grade” contractual API for production apps**; **symbol convention risk** — US listings often encoded as **`{ticker}.us`** with hyphenation for multi-class dots (e.g. **BRK.B** → **`brk-b.us`** — heuristic in-repo); **not adjusted** in the same sense as vendor “adjusted close” products — treat field semantics carefully.
- **Terms:** Use only in compliance with Stooq’s published terms; no scraping of pages outside documented usage.

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
| **API key requirement** | Alpha Vantage / Polygon / Tiingo: yes. Stooq public CSV: no. yfinance: no key but unofficial. |
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
| **Main R2 (current)** | **Design** + **`config/us_market_data.yaml`** + **`build_us_provider_preview_plan`** / **`debug us-provider-preview`** — **no HTTP**, **no live ingestion**. |
| **Main R3** | **Gated live preview** — **one provider**, **one symbol**, triple-gated CLI (explicit flags + env), response parsed to **sanitized** structures only — still **optional** cache write behind confirmation. |
| **Main R4** | **Cache write path** wired with **human confirmation**, logging policy, and **no `raw_response` in payloads**. |

---

## 5. Default recommendation

1. Keep **manual file / fixture import** as the **fallback** forever (repro CI, outages, auditing).
2. For **automated** use, prefer a provider with an **explicit, stable HTTPS API** and acceptable **ToU for your use-case** (e.g. Alpha Vantage for prototyping; **Polygon/Tiingo-class** APIs for clearer commercial footing when budget allows).
3. **Avoid** coupling core automation solely to **unofficial Yahoo / HTML scraping**.
4. **Safety:** **No live HTTP by default.** **No API keys printed.** **`raw_response` never written.** All provider outputs must pass the **sanitized OHLCV cache writer** (`save_us_daily_bars_cache`) after validation.
