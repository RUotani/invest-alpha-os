# R6.18-B+C — Implementation review pack (planning)

**日付**: 2026-05-20  
**性質**: **implementation ではない** · 将来の B1 実装承認用

---

## 1. Proposed Implementation Scope

```text
B1 only: opt-in signals --us-cache-preview
```

- 既存 `append_us_cache_preview_section` / preview table builder を **signals 出力パス**に接続
- **default daily / signals 不変**
- **no scoring** · **no ranking 変更** · **no Veto/portfolio/macro**

---

## 2. Files Likely to Change (future PR)

| ファイル | 変更想定 |
|---|---|
| `src/invis_alpha_os/cli/main.py` | `signals` に `--us-cache-preview` Option |
| `src/invis_alpha_os/reports/us_cache_preview_opt_in.py` | signals 向け append ヘルパ（または既存関数の再利用） |
| `tests/test_us_cache_preview_opt_in.py` | signals default/opt-in · forbidden terms |
| `docs/01_development_status.md` | R6.18 実装ステータス |
| `docs/69_*` runbook | signals opt-in 手順（軽量追記） |

**変更しない想定**: workflow · Makefile · pyproject · Veto · portfolio · macro modules

---

## 3. Tests Likely to Change (future PR)

- `test_signals_default_excludes_us_cache_preview`
- `test_signals_opt_in_includes_us_cache_preview`
- `test_daily_default_unchanged`（回帰）
- forbidden terms · no live HTTP · no cache write（signals パス）
- stale / freshness_unknown note 契約

---

## 4. Risks

| risk | mitigation |
|---|---|
| signals JSON に preview が混入し parser が壊れる | markdown 節分離、または json 時は別キーで明示分離 |
| momentum rank と preview の混同 | 別セクション · 別ヘッダ · テストで分離 |
| default  accidental enable | CLI default=False · golden default-off |
| stale 行の return 解釈 | 既存 note 契約 · freshness gate テスト |
| duplicate builder ロジック | `us_cache_preview_opt_in.py` 単一ソース |

---

## 5. Architecture Boundaries

| layer | 責務 |
|---|---|
| `us_daily_bars_metrics` | metrics 計算のみ |
| `us_cache_preview_opt_in` | observation-only 行の整形 |
| CLI | **opt-in 表示制御のみ** |
| signals momentum / Veto | **preview と非結合** |

**禁止**: signal scoring への preview 入力 · portfolio/macro/Veto 結合 · live/cache write パス

---

## 6. Open Questions

1. `signals --format markdown` 時のみ preview 節か、json にも `us_cache_preview` キーを載せるか
2. signals opt-in 時の節見出し（daily と同一 `### US Cache Preview (opt-in)` でよいか）
3. B1 安定後、default enablement を **daily のみ** / **signals のみ** / **両方** のどれから検討するか（別承認）

---

## 7. Stop Conditions (implementation Longpack)

- CI fail（同一原因 2 回）
- default パスに preview が出現
- forbidden term 検出
- live HTTP / cache write テスト失敗
- workflow/Makefile/pyproject への scope creep
- Codex `BLOCKED_REVISE_PLANNING` または implementation `BLOCKED`

---

## 8. Review Recommendation

| タイミング | レビュー |
|---|---|
| planning PR（本パッケージ） | **Codex** — `.agent/r6_18_bc_codex_review_prompt.md` |
| B1 implementation PR 前 | Codex read-only + 必要なら Claude arch（default 触る場合のみ） |
| default enablement PR | Codex + Claude + operator sign-off + [docs/75](./75_r6_18_bc_default_enablement_readiness_checklist.md) 全項目 |

---

## 9. 関連

- Design: [docs/74](./74_r6_18_bc_cache_only_connection_design.md)
- Implementation Longpack draft: [.agent/r6_18_bc_implementation_longpack_draft.md](../.agent/r6_18_bc_implementation_longpack_draft.md)
