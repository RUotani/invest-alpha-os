# R6.12-E — US signals daily report opt-in CLI

**ステータス**: **完了・main反映済み**（`4b0aee8` · branch CI `25924983580`）。次は **R6.12-G** hardening。

---

## 1. 目的

- `alpha-os daily --us-signals-dry-run-manifest PATH` で US signals dry-run 節を **opt-in** 追加
- **default daily 出力は flag なしで完全に従来通り**

## 2. 非目的

- config フラグ · 自動 manifest 生成 · 自動 cache 走査
- live HTTP · production cache write
- Veto / portfolio / macro · buy/sell 推奨文言

## 3. CLI

```bash
alpha-os daily --us-signals-dry-run-manifest tests/fixtures/us_equities/us_cache_signals_batch_minimal.json
```

- `path_base`: repository root（R6.12-C 契約）
- flag 省略時: manifest 未読 · US dry-run 節なし

## 4. 実装

- `reports/us_signals_opt_in.py` — `append_us_signals_dry_run_section`
- `cli/main.py` — `daily` が flag 時のみ helper 呼び出し
- invalid manifest: 節内 `*(dry-run skipped: manifest_invalid)*` · **exit 0**

## 5. 次候補

- **R6.12-F**: hardening / snapshot / invalid UX 設計
- **R6.13-A**: config flag 統合（任意）
