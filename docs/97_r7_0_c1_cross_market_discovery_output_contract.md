# R7.0-C1 — JP/US Cross-Market Discovery Output Contract

**日付**: 2026-05-20 · **main 起点**: `111f122` · **性質**: docs + 共通整形ヘルパー + tests（scanner ロジック変更なし）

---

## 1. Purpose

R7.0-C で US scanner が main に入ったため、`discover-jp` / `discover-us` を **同一視点**で比較・統合できる出力契約を固定する。

- Gmail 日次レポート統合（将来）
- operator-runner / task YAML（将来）
- 横断 Markdown / JSON レポート（将来）

**境界**: observation-only · cache read-only · live HTTP なし · 売買推奨なし · daily/signals default 変更なし

---

## 2. Field comparison (before alignment)

| 観点 | JP (`discover-jp`) | US (`discover-us`) | C1 整合 |
|---|---|---|---|
| 銘柄 ID | `code` | `symbol` | `common_candidates[].instrument_id` |
| 表示名 | `code_name` | `symbol_name` | `display_name` |
| 市場 | 暗黙 JP | 暗黙 US | `market` = `jp` \| `us` |
| スコア/ラベル | `discovery_score`, `labels`, `categories` | 同左 | 共通キー維持 |
| リターン | r1/r5/r20/r60 | 同左 | 共通キー維持 |
| 出来高 | `volume_ratio_25d` | 同左 + `volume_status` | US は値、JP は `null` |
| JSON safety | observation のみ | + `cache_read_only`, `live_http` | **両方に統一** |
| Markdown 表 | `code/name` 列 | `symbol/name` 列 | **`instrument` 列に統一** |
| Markdown グループ | Candidate Groups あり | なし（C 時点） | **US も同セクション追加** |

**後方互換**: CLI JSON の `candidates[]` / `insufficient[]` は市場別フィールド名のまま維持。

---

## 3. Common candidate schema (`common_candidates[]`)

`schema_version`: `discovery.cross_market.v1`

| キー | 型 | 説明 |
|---|---|---|
| `market` | str | `jp` or `us` |
| `instrument_id` | str | wire code or US ticker |
| `display_name` | str | 人間向け表示（R6.19-A） |
| `discovery_score` | int | 並び替え補助のみ（not trading score） |
| `latest_date` | str | 最終 bar 日付 |
| `close` | float \| null | 終値 |
| `return_1d` … `return_60d` | float \| null | 小数（例 0.12 = 12%） |
| `volume_ratio_25d` | float \| null | 25 日平均比 |
| `high_distance_pct` | float \| null | 52w high 距離 |
| `volume_status` | str \| null | US: high/normal/low/unknown · JP: null |
| `labels` | list[str] | 観測ラベル |
| `categories` | list[str] | グループ分類 |
| `data_quality` | str | ok / insufficient_history / invalid_bars |
| `bar_count` | int | bar 本数 |
| `reason` | str | 人間向け短文 |

---

## 4. JSON envelope (per market)

`discover-jp --format json` / `discover-us --format json`:

```json
{
  "schema_version": "discovery.cross_market.v1",
  "market": "jp",
  "universe_scope": "...",
  "generated_at": "...",
  "safety": {
    "observation_only": true,
    "no_trading_advice": true,
    "discovery_score_disclaimer": "...",
    "cache_read_only": true,
    "live_http": false,
    "market": "jp"
  },
  "summary": { "symbol_count": 0, "ranked_candidate_count": 0, "insufficient_count": 0 },
  "common_candidates": [],
  "common_insufficient": [],
  "candidates": [],
  "insufficient": []
}
```

- **`common_*`**: 横断比較・runner 用
- **`candidates` / `insufficient`**: 既存 CLI 互換（JP=`code`、US=`symbol`）

### 4.1 Merged payload (helper only · no CLI yet)

`merge_cross_market_json_payloads(jp_json, us_json)` → `markets.jp` / `markets.us` に `common_*` と `summary` を格納。  
将来の `discover-cross` や Gmail 統合セクションの入力契約として利用。

---

## 5. Markdown policy

| セクション | JP | US |
|---|---|---|
| Title | JP Universe Discovery Candidates | US Universe Discovery Candidates |
| Universe scope | `market`, `scope`, `symbols scanned`, `generated_at`, `live_http: false` | 同左 |
| Ranked table | 共通ヘッダ（`instrument` 列） | 同左 |
| Candidate Groups | 6 カテゴリ | 同左（C1 で US 追加） |
| Insufficient bullets | 最大 15 件 | 同左 |
| Next Research Checklist | JP 向け bullets | US 向け bullets |

---

## 6. Implementation map

| ファイル | 役割 |
|---|---|
| `discovery/cross_market_contract.py` | 共通キー・JSON envelope・Markdown 表/グループ |
| `discovery/jp_universe_scanner.py` | `format_jp_*` が contract を利用 |
| `discovery/us_universe_scanner.py` | `format_us_*` が contract を利用 |
| `tests/test_discovery_cross_market_contract.py` | 契約・merge・表ヘッダ |

---

## 7. Future hooks (not in C1 scope)

| 接続先 | 方針 |
|---|---|
| Gmail 07:00 | `common_candidates` 上位 N を日本語ナラティブ節へ（opt-in・別 PR） |
| operator-runner | task YAML で `discover-jp` + `discover-us` → `merge_cross_market_json_payloads` |
| `discover-cross` CLI | C2 以降で検討（C1 は helper のみ） |

---

## 8. Safety (unchanged)

- No live HTTP · no cache write · no trading recommendation terms
- Forbidden terms enforced via `assert_no_forbidden_terms` on Markdown/JSON blobs

---

## 9. Verification

```bash
pytest -q tests/test_discovery_cross_market_contract.py \
  tests/test_jp_universe_scanner_mvp.py tests/test_us_universe_scanner_mvp.py
```
