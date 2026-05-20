# R6.18-B+C — Cache-only connection design (planning)

**日付**: 2026-05-20 · **main 起点**: `ba38ee9`  
**性質**: **planning only** · **default enablement 未承認** · **product code 変更なし**

---

## 1. State and Problem

| 項目 | 状態 |
|---|---|
| US cache inventory | total **16** · ok **16** · fresh_enough **16** · stale **0**（R6.17-D 後） |
| `daily --us-cache-preview` | **opt-in** · 動作確認済み（R6.17） |
| `signals` | US cache preview **未接続** |
| システム性質 | **observation-only** · 売買推奨エンジンではない |

**課題**: 手動 opt-in preview は安全だが運用価値が限定的。**daily / signals の decision materials へ cache-only で接続する経路**を設計し、**default は別承認までブロック**する。

---

## 2. Connection Principles

- **cache-only** — 既存 `outputs/market_data/us_daily_bars/` の read-only のみ
- **opt-in first** — 明示フラグなしでは preview を出さない
- **default unchanged** — 別 PR・別承認まで daily/signals default 不変
- **no live HTTP by default** — preview パスに HTTP を載せない
- **no cache write by default** — operator gated refresh は別手順（R6.17-D 等）
- **no aggregate score** — 本フェーズではランキング・合成スコアなし
- **no buy/sell/recommendation language** — output contract で禁止
- **no portfolio allocation** · **no macro regime** · **no Veto connection**
- **stale / freshness_unknown** — returns / volume の解釈に使わない（note で明示）
- **output contract testable** — 列・禁止語・default-off をテストで固定

---

## 3. B-Path Options

### B0 — Keep manual daily opt-in only

- **現状**（R6.17 完了）
- **最も安全** · signals には未接続
- 運用 utility は限定的（daily のみ手動）

### B1 — Add opt-in `signals --us-cache-preview`（推奨）

- 既存 preview builder / output contract を **signals 出力に再利用**
- **no scoring** · **no ranking 変更** · **no trading terms**
- daily default / signals default **ともに不変**
- **R6.18 実装候補: B1 のみ**

### B2 — Add daily report appendix by default, but clearly non-trading

- **現時点では非推奨**
- default enablement 承認 + 監視強化が前提
- [docs/75](./75_r6_18_bc_default_enablement_readiness_checklist.md) の全 precondition 必須

### B3 — Connect to scoring / portfolio / Veto

- **明示的に out-of-scope**

---

## 4. Recommended B Scope

```text
R6.18 implementation candidate: B1 only
```

B1 の意味:

- `signals` CLI / markdown（または json 併記）に **opt-in preview 節**を追加
- `reports/us_cache_preview_opt_in.py` の builder を再利用（重複実装しない）
- `daily` default **変更なし**
- `signals` default **変更なし**
- momentum ranking · Veto · portfolio / macro **触らない**

---

## 5. Output Contract

### 5.1 Allowed columns

| column | 説明 |
|---|---|
| `symbol` | ティッカー |
| `latest_date` | 最新 bar 日付 |
| `freshness_status` | `fresh_enough` / `stale` / `freshness_unknown` 等 |
| `close` | 終値 |
| `return_1d` | 1 日リターン（fresh_enough のみ意味あり） |
| `return_5d` | 5 日リターン |
| `return_20d` | 20 日リターン |
| `volume_status` | `normal` / `high` / `low` / `unknown` |
| `note` | observation-only（stale 等） |

### 5.2 Allowed labels

- freshness: `fresh_enough` · `stale` · `freshness_unknown`
- volume: `normal` · `high` · `low` · `unknown`
- note: observation-only（例: `stale — returns not used`）

### 5.3 Forbidden terms（preview 節内）

`buy` · `sell` · `recommendation` · `allocate` · `allocation` · `portfolio` · `veto` · `macro` · `production` · `overweight` · `underweight` · `target price` · `entry` · `exit`

### 5.4 Stale / freshness_unknown

- 行は **表示可**（inventory 準拠）
- `return_*` は **解釈に使わない**（note 必須 · 既存 R6.17 契約）
- signal scoring / momentum rank への入力 **禁止**

---

## 6. Tests Required for Later Implementation

| # | テスト |
|---|---|
| 1 | daily default excludes preview |
| 2 | signals default excludes preview |
| 3 | daily opt-in includes preview |
| 4 | signals opt-in includes preview |
| 5 | forbidden terms absent from preview section |
| 6 | no live HTTP（urlopen / provider 未使用） |
| 7 | no cache write |
| 8 | stale / freshness_unknown — returns not used（note 契約） |
| 9 | no product behavior change without flag |
| 10 | output contract snapshot / golden |
| 11 | missing / invalid cache handled safely |

---

## 7. Non-Goals

- default enablement（daily / signals）
- scoring · allocation · trading recommendation
- live ingest · cache refresh automation
- macro / Veto / portfolio connection
- workflow / Makefile / pyproject 変更（本 planning PR では含めない）

---

## 8. 関連

- R6.17 実装: [docs/67](./67_r6_17_opt_in_us_cache_preview_implementation.md)
- Operator runbook: [docs/69](./69_r6_17_b_opt_in_us_cache_preview_runbook.md)
- Stale refresh 記録: [docs/73](./73_r6_17_d_stale_refresh_status.md)
- Default readiness: [docs/75](./75_r6_18_bc_default_enablement_readiness_checklist.md)
- Implementation review: [docs/76](./76_r6_18_bc_implementation_review_pack.md)
