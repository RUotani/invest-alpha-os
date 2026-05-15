# R6.12-D — US signals daily report opt-in design

**ステータス**: **完了・main反映済み**（`1e4013c` · branch CI `25924652445`）。実装は **R6.12-E** へ。

---

## 1. 目的

- R6.12-C batch manifest + R6.12-B multi-symbol dry-run renderer を、**将来** daily report へ **opt-in** で接続する設計を固定する
- **default daily report 出力は変更しない**

## 2. 非目的

- daily report 本体実装 · CLI 実装 · config 実装
- 自動 cache 走査 · watchlist 自動実行
- live HTTP · production cache write
- Veto / portfolio / macro 接続

## 3. opt-in の意味

- `alpha-os daily`（または同等エントリ）の **既存 JP/US momentum 節はそのまま**
- 明示フラグ（config / CLI / env いずれか一つに限定予定）が **ON のときのみ**、追加節 `## US Signals Dry Run` を末尾または専用 appendix に挿入

## 4. 推奨 render flow

```text
manifest_path (explicit JSON)
  → build_us_cache_signals_previews_from_batch_manifest(path_base=REPO_ROOT)
  → render_us_cache_signals_multi_symbol_dry_run_section(previews)
  → opt-in section string（daily 組み立て時に concat のみ）
```

- `path_base`: repository root（R6.12-C と同一）
- manifest は **手動管理**（自動生成しない）

## 5. config / CLI flag 候補

| 候補 | 備考 |
|------|------|
| `config/us_report.yaml` → `us_signals_dry_run.enabled` | 運用向き · default `false` |
| `alpha-os daily --us-signals-dry-run-manifest PATH` | 一回限りの明示パス · 最も安全 |
| 環境変数 | 本フェーズでは **採用しない**（`.env` 非目標と整合） |

**推奨（実装フェーズ R6.12-E）**: CLI optional `--us-signals-dry-run-manifest` のみ。config は後続。

## 6. failure handling

- manifest invalid: **節全体をスキップ**し、daily 本体は成功終了（exit 0 維持）
- 節内に短い `*(dry-run skipped: manifest_invalid)*` を1行
- preview 行の per-symbol invalid は R6.12-C どおり行単位で表に残す

## 7. output contract

- R6.12-B multi-symbol dry-run Markdown を **そのまま** 使用（再フォーマットしない）
- 見出し重複を避けるため、daily 側は `### US Signals Dry Run (opt-in)` など一段下げる案

## 8. 次候補

- **R6.12-E**: opt-in implementation（CLI flag + tests · still non-default）
