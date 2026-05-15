# R6.10-D — US cache preview / diagnostics hardening

**ステータス**: 作業ブランチ `work/r6-10-d-us-cache-preview-hardening` のみ。**`main` 未反映**。

---

## 1. 目的

- R6.10-C **`debug us-daily-bars-cache-preview`** の **JSON / Markdown 出力契約**をテストで固定
- **異常系**（invalid path · invalid JSON · invalid envelope · symbol mismatch · bad `--format`）の CLI 回帰を追加
- **live HTTP / production cache write なし**を維持

## 2. 方針（パターンA）

- **`PREVIEW_OK_KEYS`** / **`PREVIEW_INVALID_BASE_KEYS`** で JSON キー集合を明示
- invalid Markdown に **`live_http: false`** を常に含める
- `tests/test_cli_us_daily_bars_cache_preview.py` に契約・異常系テストを追加

## 3. 非目的

- live HTTP / production cache write / US scoring / portfolio / report 大規模統合なし

## 4. 出力契約

| 状態 | JSON キー | CLI exit |
|------|-----------|----------|
| ok | `PREVIEW_OK_KEYS` 固定 | 0 |
| invalid | `validation_status` · `reason` · `path` · `live_http`（＋必要時 `expect_symbol`） | 1 |
| bad `--format` | （出力なし・stderr メッセージ） | 2 |

## 5. テスト方針

- fixture / tmp_path envelope
- duplicate date · unsorted · `bar_count` mismatch · empty `bars` → `parse_failed`
- `urlopen` ブロック（live HTTP 禁止）
