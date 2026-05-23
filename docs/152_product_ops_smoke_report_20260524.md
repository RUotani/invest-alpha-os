# Product — ops smoke report (2026-05-24)

**Status**: read-only verification · no writes in this report  
**Environment**: local repo `outputs/market_data/us_daily_bars/`（16 US symbols cached）

---

## 実行コマンドと結果

### 1. weekly-us-observation（dry-run + peer-sync）

```bash
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation \
  --dry-run --with-peer-sync --format markdown
```

**Exit code**: 0

**要点**

| 項目 | 値 |
| --- | --- |
| Manifest entries | 16 |
| Missing cache | 0 |
| Signals batch | ok / 16 previews |
| Quality | 16/16 ok, veto 0 |
| Peer sync pairs | 2 evaluated |
| Diverged | AAPL vs MSFT (-5.70%), AAPL vs GOOGL (-4.35%) |
| Tier-1 gap | AMD（gated refresh 対象・**未実行**） |

**判定**: ✅ レポート構造 OK。peer_sync セクションが weekly に統合されている。

---

### 2. validate peer-sync

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync --format markdown
```

**Exit code**: 0

**要点**

- peer_map: `config/peer_map.yaml`
- 2 pairs: いずれも `diverged_peer_outperform`
- AAPL→MSFT: spread -5.70%, corr -0.12, aligned 69 sessions
- AAPL→GOOGL: spread -4.35%, corr 0.16, aligned 5472 sessions

**判定**: ✅ 出力 readable。GOOGL aligned 数が大きい（cache 履歴長）— 観測用途では許容。

**修正済み（follow-up PR）**: next_commands の stale 文言（weekly 未統合表記）を更新。

---

### 3. snapshot portfolio-observation-summary

```bash
.venv/bin/python -m invis_alpha_os.cli.main snapshot portfolio-observation-summary --format json
```

**Exit code**: 0

```json
{
  "shadow_position_count": 0,
  "observation_row_count": 0,
  "positions_with_evidence_ids": 0,
  "positions_with_resolved_links": 0
}
```

**判定**: ✅ 空データでも valid JSON。shadow / observation_log 未使用の初期状態と一致。

---

## 明示的に未実行（方針通り）

| コマンド | 理由 |
| --- | --- |
| `weekly-us-observation --write-observation-log` | ローカル `outputs/` 書込 — 必要時のみ明示承認 |
| P10 tier-1 refresh | live HTTP / cache write — **実行禁止** |
| `log peer-sync-snapshot` | 同上（follow-up PR で CLI 追加、実行は opt-in） |

---

## 推奨次ステップ（人間）

1. 週次運用開始時: docs/150 の `--write-observation-log` を **明示承認後** 実行
2. PR マージ後: `log peer-sync-snapshot` で peer 行を optional append
3. tier-1 AMD refresh は docs/151 チェックリスト + 承認後のみ

---

## Raw captures（参考）

ローカル only: `.agent/ops_smoke/01_validate_peer_sync.md` 等（git 非推奨）
