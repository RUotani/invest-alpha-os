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

**stale 方針**: §5 に確定（プレビュー表では **明示マーク + 警告** · signal scoring には使わない）。

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

## 5. 確定方針（実装前レビュー用 · planning）

### 5.1 Stale handling（確定）

- **プレビュー表**: `stale` シンボルは **含めてよい**が、`freshness_status` で **明示マーク** 必須（inventory の `freshness_status` をそのまま表示）
- **警告**: 1 件でも `stale` があればプレビュー節に **warning 行**（例: `note` / `warning` 列または節頭注記）
- **signal scoring**: `stale` / `freshness_unknown` は **入力に使わない**（プレビュー表示のみ）
- **fresh_enough 判定**: inventory freshness 拡張（R6.16-E）の `freshness_status` に準拠
- **禁止**: stale を valid signal input として **黙って扱う**こと

### 5.2 Benchmark requirements（初期確定）

| シンボル | 役割 |
|---|---|
| **SPY** · **QQQ** | コア benchmark |
| **TLT** · **GLDM** | regime / risk 参考 |

- **初回 preview**: benchmark が `stale` でも **停止しない**（表に載せ warning）
- **将来 hard gate（production 前）**: SPY/QQQ が `fresh_enough` でない場合は production use をブロック可能（**R6.17 初期実装では未適用**）

### 5.3 First preview symbol set（初期）

- **watchlist 全 16**（inventory と同じ universe）を第一候補
- subset 化は実装 PR でフラグ化可能だが **default は全件表示**

### 5.4 Output columns（許可 / 禁止）

**許可列（初期）**:

- `symbol` · `latest_date` · `freshness_status` · `close`
- `return_1d` · `return_5d` · `return_20d`
- `volume_status`
- `note` または `warning`

**禁止（列・節とも）**:

- buy/sell recommendation · portfolio allocation
- Veto 統合 · macro regime **最終判断**
- default daily report 節の **自動 enable**

### 5.5 Tests / golden（要件）

- **opt-in フラグ ON 時のみ** golden / fixture 更新
- **env 非依存**（`JQUANTS_*` 不要）
- default パス golden は **変更しない**

### 5.6 実装 PR で確定（Claude review 反映）

- **`volume_status`**: prior-25 平均（最新 bar 除外）· ratio ≥2.0 high · &lt;0.5 low · それ以外 normal · prior &lt;5 → unknown
- **`return_1d`**: horizons `[1, 5, 20]` · `METRICS_PREVIEW_OK_KEYS` に含める
- **warning 文言**: `stale — returns not used` · `freshness unknown — returns not used`

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
