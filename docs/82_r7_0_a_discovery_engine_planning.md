# R7.0-A — Discovery engine planning

**日付**: 2026-05-20 · **性質**: planning only · **実装なし**

---

## 1. Original Goal

The long-term goal is not merely watchlist monitoring.

The goal is cross-sectional discovery across JP and US equities: early detection of rapid movers, breakout/volume anomalies, and emerging market reputation/narrative signals, then outputting **deep-dive candidates** for human/ChatGPT review.

---

## 2. Current System Boundary

| 現状（R6） | 内容 |
|---|---|
| Named watchlist | JP momentum · US cache preview（opt-in） |
| Operator utility | daily usage bundle · Gmail（R6.19） |
| **Not yet** | 市場横断スキャン · reputation 層 · 自動売買推奨 |

---

## 3. Target Capabilities

- JP universe scanner
- US universe scanner
- price/volume breakout · 52w high · gap/volume anomaly
- cross-sector ranking
- news/disclosure/narrative layer（後 phase）
- reputation/watch signal layer（後 phase）
- candidate report · ChatGPT deep-dive prompt · Gmail delivery

---

## 4. Data Sources

### Price/volume

- local cache · J-Quants（JP）· US provider cache · CSV fallback

### Universe lists

- JP listed / segment filters · US S&P500/Nasdaq100/ETF · user watchlists

### Reputation/news（deferred）

- TDnet/EDINET · earnings calendar · headlines · analyst changes
- Google Trends / social — **別承認** · noise policy 必須

---

## 5. MVP Phasing

### R7.0-B — JP Universe Scanner MVP

- price/volume only · broad JP subset
- rank: r1/r5/r20 · volume ratio · 52w proximity · liquidity · overheat
- **no** trading recommendation

### R7.0-C — US Universe Scanner MVP

- S&P500/Nasdaq100/ETF universe · same metrics

### R7.0-D — Reputation/News Layer MVP

- headlines/disclosures · theme classification · unexplained move flag

### R7.0-E — Discovery Daily Report

- top candidates · new/continuing/overheated movers · ChatGPT prompt · Gmail

---

## 6. Output Contract

**Use**: deep-dive candidate · observation · alert · follow-up · material check · liquidity check · overheat caution

**Avoid**: buy · sell · recommendation · allocation · target price · entry/exit instruction

---

## 7. Safety Gates

- no trading recommendation · no portfolio allocation · no auto-order
- no default inclusion in daily operator report until reviewed
- low-liquidity pumps require warning
- reputation/social requires source/noise caveat
- every candidate includes **why surfaced**

---

## 8. Review Requirements

- Codex read-only planning review（`.agent/r7_0_a_discovery_engine_planning_codex_prompt.md`）
- Claude architecture review if source architecture changes
- **R7.0-B implementation Longpack** only after planning approval

---

## 9. R7.0-B Implementation Draft Scope（placeholder）

- read-only JP universe ingest plan · liquidity filter · ranking table CLI
- **no** reputation layer · **no** default enablement · **no** live HTTP without existing gates

---

## 10. 関連

- Daily operator: [docs/81](./81_r6_19_b_daily_0700_gmail_delivery_runbook.md)
- R6.19-A Gmail: [docs/80](./80_r6_19_a_gmail_delivery_and_display_names.md)
