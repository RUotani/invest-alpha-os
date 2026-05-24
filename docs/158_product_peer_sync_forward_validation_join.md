# Product — peer_sync × forward validation join (read-only)

**Status**: implemented · cache-only · observation only  
**Related**: [docs/147](./147_product_p9_p11_observation_veto_forward_usability.md), [docs/150](./150_product_observation_log_weekly_runbook.md)

---

## 目的

`observation_log.jsonl` の `us_peer_sync` 行を、同一 anchor シンボルの **cache-only forward returns** に日付で join し、`by_peer_sync_status` バケットで観測品質を確認する。

## 設計

| 項目 | 方針 |
| --- | --- |
| 入力 | `us_peer_sync observation_only` note 行（`parse_us_peer_sync_observation_note`） |
| イベント日 | 行の `created_at`（US forward validation と同じ `_parse_event_date`） |
| 価格 | `try_load_bars_for_peer_sync(anchor)` — US cache / JP J-Quants cache |
| 出力 | `by_peer_sync_status`, `peer_sync_at_t`, `sample_quality` |
| HTTP | **なし** |
| outputs 書込 | **なし** |

## CLI

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync-forward-returns --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown
```

`validate us-forward-returns` レポートには `peer_sync_forward` ブロックが自動同梱される。

`snapshot observation-health`（docs/153）でも `peer_sync_rows` > 0 のとき同じ join 結果を `peer_sync_forward` として出力する。

## `peer_sync_at_t` ステータス

| status | 意味 |
| --- | --- |
| `not_in_observation_log` | peer_sync 行が 0 件 |
| `joined` | 1 件以上 join 試行（matched は cache 依存） |

## 解釈

- observation only — 取引推奨ではない
- `thin` / `empty` はサンプル不足。週次 `log peer-sync-snapshot` + forward 蓄積を継続
