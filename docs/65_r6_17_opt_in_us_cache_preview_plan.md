# R6.17 — Opt-in US cache-only preview (planning)

**ステータス**: **planning / ブランチ作業のみ**（**`main` 未反映** · **実装なし**）。ブランチ: **`work/r6-17-opt-in-cache-preview-plan`**。  
**性質**: 設計・Longpack 下書きのみ。**daily / signals default は変更しない**。

---

## 1. 目的

- US **cache-only** データを daily / signals へ **opt-in** でプレビューする
- **default 変更なし** · **production decision にはまだ使わない**
- **freshness** をゲートに使う（初期: `latest_date >= today - 7` 暦日）
- **output contract**（列・脚注・stale 表示）を先に固定する

---

## 2. 前提（`main` 現状）

| 項目 | 状態 |
|---|---|
| US cache inventory | ok **16** / missing **0**（R6.16-D 運用記録） |
| Freshness extension | **main** · PR #11 · `39304a1` |
| Freshness 初期閾値 | **7 暦日** cutoff |
| Stale 例 | 一部シンボルは `stale` になり得る（fixture / 古い bar） |
| daily / signals default | **接続なし**（別承認） |
| cache JSON / `.env` | **local / gitignore** |

**stale 方針（要決定）**: プレビューから **除外** / **警告付き表示** / **明示マーク** のいずれか（§5）。

---

## 3. 許可する初期 R6.17 scope（実装 PR 用）

- read-only cache load（既存 inventory / bar 読み取りの再利用）
- **opt-in CLI flag のみ**（例: daily report 用プレビュー節）
- **Markdown プレビュー節のみ**（新規セクション · 既存 default パス不変）
- freshness gate · output contract テスト

## 4. 禁止する scope

- US signals **default** enable
- daily report **default** 節 enable
- live provider fallback
- cache auto-refresh / **cache write**
- production write
- portfolio / macro / **Veto** 接続
- 売買推奨・自動 instruction

---

## 5. Design questions（実装前に決める）

1. **Stale symbols**: プレビューに含めるか · 除外か · `STALE` 列で明示か
2. **Benchmark freshness**: SPY/QQQ 等を **all fresh enough** 必須にするか
3. **First preview symbol set**: watchlist 全16 vs コア subset
4. **Output columns**: 許可列のみ（symbol · latest_date · freshness_status · close? · 注記）
5. **Tests / golden**: opt-in 時のみの fixture · env 非依存

---

## 6. 提案 execution path（実装 Longpack 用 · 未実行）

1. 本設計 doc + ChatGPT / Claude arch review（default 変更なし確認）
2. read-only cache loader helper（不足時のみ · 最小）
3. opt-in CLI flag
4. markdown preview section + contract doc
5. tests（opt-in path のみ）
6. CI
7. Codex PR review
8. **merge は ChatGPT / ユーザー承認まで待つ**

---

## 7. 関連

- [docs/63_r6_16_e_us_cache_inventory_freshness.md](./63_r6_16_e_us_cache_inventory_freshness.md)
- [docs/62_r6_16_d_us_cache_full_population_status.md](./62_r6_16_d_us_cache_full_population_status.md)
- `.agent/r6_17_cursor_longpack_draft.md`（**下書き · 実行しない**）
