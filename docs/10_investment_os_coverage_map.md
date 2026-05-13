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
| **Total Investment OS** (all rows in §3 treated as one programme) | **about 30–40%** | Most non-JP pillars are latent or conceptual |

These numbers are **judgment calls for planning**, not audited metrics.

---

## 3. Scope table

Status legend (short): **N/S** not started · **Conc** conceptual / backlog · **Partial** early integration · **Active** recurring use in-repo.

Progress % is directional (same caveat as §2).

| Area | Implementation status | Progress % | Data source status | Signal status | Report status | Next priority |
|------|-------------------------|------------|--------------------|--------------|---------------|---------------|
| **JP equities / J-Quants** | Cache-backed daily bars → signals → daily Markdown | ~80–85% | Active (local sanitized JSON cache; optional live ingest behind gates elsewhere) | Momentum Score v2 + CLI | Daily section + Observations + Action Watchlist (cache-only) | Liquidity/context fields, QA on edge cases |
| **US equities** | Main R / **Main R1**: **`us_watchlist.yaml`** + **`us_daily_bars_cache`** + **CLI/file fixture import** + optional gated US momentum renderer — **still no vendor HTTP ingest** | **~15–20%** | **Local fixture → cache path works; provider data fetching still not implemented** | Momentum-ready when cache populated (local JSON) | Hidden from daily unless `include_us_momentum_cache_only_section` | Wire optional provider ingestion behind gates when ready |
| **US ETFs** | Same tray as US equities (watchlist grouping + shared cache/import path) | **~15–20%** | **No fetch wired** — local JSON convention + Main R1 import only | As above | As above | Bundled under **Main R / R1** slice |
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
- **Main R1**: added committed **`tests/fixtures/us_daily_bars/`** OHLCV JSON, **`debug us-daily-bars-cache-import`** (dry-run / `--write-cache`), **`make us-cache-fixture-import`**, and **`make us-momentum-check`** — **fixture-based cache population only**; **US market data fetching from a vendor is still not implemented**.
- **US equities / ETFs / listed crypto proxies**: now roughly **stage 1–2** for configuration and **stage 3-ish** *only after* you populate `outputs/market_data/us_daily_bars/*.json` manually (no automated ingest in-repo yet).
- **Metals**, **rates** (non-proxy): unchanged backlog until **Main S**.
- **Macro regime**: conceptual and doc-level; **not fully integrated** as a repeatable data + signal pipe in-repo.
- **Portfolio-aware decision support**: **still early** (aligns roughly with stages **1–3** depending on subsystem).

---

## 6. Recommended next sequence

After Main Q / Q0:

| Phase | Theme |
|-------|--------|
| **Main R / R1** | US equities / ETF — **local fixture/cache import prototype** (`us_watchlist`, cache schema, CLI + Makefile targets); **provider / live HTTP ingest remains future work** |
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
