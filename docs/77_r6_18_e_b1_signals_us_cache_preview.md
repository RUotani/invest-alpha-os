# R6.18-E — B1 opt-in signals US cache preview（実装）

**日付**: 2026-05-20
**性質**: **B1 only** · **opt-in** · **default 変更なし** · **main** `9c6f5e5` / PR **#23**

---

## 1. 実装内容

| 項目 | 内容 |
|---|---|
| CLI | `signals --us-cache-preview`（**default off**） |
| JSON 出力 | トップレベル `us_cache_preview` キー（preview dict） |
| Markdown 出力 | `append_us_cache_preview_section` で observation-only 節を追記 |
| 再利用 | `reports/us_cache_preview_opt_in.py`（daily と同一 builder） |

**変更なし**: `daily` default · `signals` default · scoring / ranking / Veto

**エッジ経路**: `--bars-file` + `--us-cache-preview` は **JSON のみ** `us_cache_preview`（Markdown preview 節なし）。運用は [docs/78](./78_r6_18_f_signals_us_cache_preview_operational_evidence.md) §3.5。

---

## 2. 境界

- **cache-only** · **no live HTTP** · **no cache write**
- **no cache JSON commit** · **no trading recommendation**
- **no portfolio / macro / Veto** 接続
- **default enablement**: [docs/75](./75_r6_18_bc_default_enablement_readiness_checklist.md) により **ブロック継続**

---

## 3. テスト

- `tests/test_us_cache_preview_opt_in.py` — signals default/opt-in · forbidden terms · no live/write guards

---

## 4. 関連

- 設計: [docs/74](./74_r6_18_bc_cache_only_connection_design.md)
- 運用 evidence: [docs/78](./78_r6_18_f_signals_us_cache_preview_operational_evidence.md)
- Planning: PR #21 · B+C docs
