# DRAFT — R6.18-G signals preview smoke evidence (do not execute)

```text
DO NOT ENABLE DEFAULT. READ-ONLY SMOKE ONLY.
```

## 目的

- `signals` default / `signals --us-cache-preview` の **read-only** smoke を実行し、[docs/78](../docs/78_r6_18_f_signals_us_cache_preview_operational_evidence.md) §4 に証拠を記入する
- **default enablement 禁止** · **product code 変更禁止**

## 前提

- `origin/main` に R6.18-F 以降が反映済み
- US cache: local `outputs/market_data/us_daily_bars/`（**commit しない**）

## 許可

- read-only CLI smoke（[docs/78](../docs/78_r6_18_f_signals_us_cache_preview_operational_evidence.md) §3）
- docs/78 evidence 表の更新（**docs-only PR**）
- inventory read-only

## 禁止

- live HTTP · cache write · cache JSON commit
- `.env` / secrets 出力
- default daily/signals preview enablement
- product / workflow / Makefile / pyproject 変更
- main direct push · force push · branch/worktree 削除

## 手順（要約）

1. `git pull --ff-only origin main` · clean tree
2. inventory（任意）
3. `signals --dry-run` → default に preview なし
4. `signals --dry-run --us-cache-preview` → `us_cache_preview` あり
5. forbidden terms（preview のみ）· live_http なしを確認
6. docs/78 §4 に **日付・commit・結果**を 1 行追加
7. 別運用日で 2 行目 — **2+ 行で G 完了**

## 最終報告

単一 Markdown コードブロック · completion sound は `.agent/standard_clauses.md` に従う。
