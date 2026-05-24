# Product — JP peer_sync loader 設計 (cache-only)

**Status**: design + readiness CLI · no live HTTP  
**Related**: [docs/158](./158_product_peer_sync_forward_validation_join.md), `config/peer_map.yaml`

---

## 目的

`peer_map.yaml` の JP エッジ（例: `7011 → 7012`）を **J-Quants daily bars cache のみ** で評価可能にする。live HTTP / cache write は本設計の範囲外。

## モジュール

`src/invis_alpha_os/product/jp_peer_sync_loader.py`

| 関数 | 役割 |
| --- | --- |
| `classify_peer_map_symbol` | `us` / `jp` 判定 |
| `try_load_bars_for_peer_sync` | US or JP cache から `DailyBar` |
| `build_jp_peer_sync_readiness_report` | JP エッジの cache 有無一覧 |

## Cache パス

- JP: `outputs/market_data/jquants_daily_bars/{wire}.json`（`try_load_cached_daily_bars`）
- US: `outputs/market_data/us_daily_bars/{SYMBOL}.json`

## CLI（read-only）

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate jp-peer-sync-readiness --format markdown
```

## 現状の peer_map

JP エッジは US cache ローダーでは `missing_cache` となる。JP cache ingest は **人間承認 + 別 runbook**（P10 tier-1 等）。

## 将来（明示承認後）

- `evaluate_peer_map` に JP bars 供給
- `validate peer-sync` で JP エッジを `ready` に近づける
