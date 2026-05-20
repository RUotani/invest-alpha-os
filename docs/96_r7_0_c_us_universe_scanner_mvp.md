# R7.0-C — US Universe Scanner MVP

**日付**: 2026-05-20 · **main 起点**: `d131d7f` · **性質**: cache-only scanner 実装（observation-only）

---

## 1. Purpose

JP `discover-jp` と同思想で、US 側の cache-only discovery 候補出力を追加する。  
live HTTP / cache write は行わず、既存 US cache を読み取りのみで利用する。

---

## 2. Scope（MVP）

- 新規 scanner: `src/invis_alpha_os/discovery/us_universe_scanner.py`
- 新規 CLI: `discover-us`
- 新規 config: `config/us_universe_scanner_mvp.yaml`
- 新規 tests:
  - `tests/test_us_universe_scanner_mvp.py`
  - `tests/test_us_universe_scanner_config.py`

**境界**:

- observation-only（売買推奨なし）
- cache read-only（`load_us_daily_bars_cache`）
- default behavior 変更なし
- daily/signals 既定フローへ自動接続しない

---

## 3. Design

### 3.1 Universe resolution

1. `--universe-file` 指定時: YAML `symbols` を使用（正規化 + first-wins dedup）
2. 未指定時: `config/us_watchlist.yaml` を既定 universe とする
3. watchlist も空なら local cache シンボルへフォールバック

### 3.2 Candidate metrics / labels

再利用:

- `calculate_returns`（r1/r5/r20/r60）
- `detect_high_breakout`
- `high_distance_vs_prior_high_pct`
- `volume_ratio_25d_prior_mean`

主ラベル:

- `high_52w_breakout`
- `near_high`
- `volume_spike`
- `rapid_mover_20d`
- `rapid_mover_5d`
- `overheat_caution`
- `low_liquidity_caution`

### 3.3 Output contract

`discover-us --format json`:

- `safety.observation_only=true`
- `safety.live_http=false`
- `summary.symbol_count / ranked_candidate_count / insufficient_count`
- `candidates[]` / `insufficient[]`

`discover-us --format markdown`:

- observation disclaimer
- ranked table
- insufficient bullets
- next research checklist

---

## 4. Local run snapshot（read-only）

ローカル証跡（未コミット）:

- `outputs/operator/discovery_eval/2026-05-20/r7_0_c/discover_us_mvp.json`
- `outputs/operator/discovery_eval/2026-05-20/r7_0_c/discover_us_mvp.md`
- `outputs/operator/discovery_eval/2026-05-20/r7_0_c/operator_summary.{json,md}`

summary:

| metric | value |
|---|---:|
| symbol_count | 16 |
| ranked_candidate_count | 14 |
| insufficient_count | 2 |

ラベル分布（ranked）: near_high 3（今回スナップショット）

---

## 5. Tests

実行:

```bash
git diff --check
.venv/bin/python -m pytest -q \
  tests/test_us_universe_scanner_mvp.py \
  tests/test_us_universe_scanner_config.py \
  tests/test_jp_universe_scanner_mvp.py \
  tests/test_jp_universe_core50_config.py
```

結果: **22 passed**

---

## 6. Safety

- secrets / `.env` / token: 出力なし
- live HTTP / cache write: なし
- `outputs/` / cache JSON: コミットなし
- trading recommendation wording: なし

---

## 7. Recommendation

R7.0-C MVP は実装完了。次は以下のいずれか:

1. **R7.0-C1**: JP/US discovery 出力の共通比較フォーマット追加
2. **R7.0-Ops-A**: task YAML / stop policy へ `discover-us` 接続
3. **並行**: JP 残り 10 銘柄 cache 埋め（B3S2 型）
