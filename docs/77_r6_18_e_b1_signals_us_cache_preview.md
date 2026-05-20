# R6.18-E — B1 opt-in signals US cache preview（実装）

**日付**: 2026-05-20  
**性質**: **B1 only** · **opt-in** · **default 変更なし**

---

## 1. 実装内容

| 項目 | 内容 |
|---|---|
| CLI | `signals --us-cache-preview`（**default off**） |
| JSON 出力 | トップレベル `us_cache_preview` キー（preview dict） |
| Markdown 出力 | `append_us_cache_preview_section` で observation-only 節を追記 |
| 再利用 | `reports/us_cache_preview_opt_in.py`（daily と同一 builder） |

**変更なし**: `daily` default · `signals` default · scoring / ranking / Veto

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
- Planning: PR #21 · B+C docs
