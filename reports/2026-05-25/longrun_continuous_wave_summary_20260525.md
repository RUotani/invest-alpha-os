# Longrun continuous wave summary — 2026-05-25

## 3行サマリー
- 停止せず **#251 · #252** を連続 MERGE（+ 承認 A/B/C 実行済み）。
- `origin/main` 最終: **#252** マージ後 SHA は CI 完了後に STATE 同期。
- forward P3 未達（fresh_log）— `validate post-refresh-smoke` で監視継続。

## PR キュー（完了）

| PR | 内容 | CI |
|---|---|---|
| #251 | skip_pattern · peer_sync co-write · post-refresh-smoke CLI · portfolio YAML | SUCCESS |
| #252 | docs/150 · forward markdown · STATE c08cffd | SUCCESS |

## 承認実行（前ターン）

| ID | 結果 |
|---|---|
| A | AMD cache 10879 bars |
| B | observation_log 74 lines |
| C | portfolio 25% → config YAML |

## 新 CLI

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate post-refresh-smoke --format markdown
```

## Post-smoke（ローカル · c08cffd）

- tier1_missing: 0
- forward matched: 0 · skip_pattern: mixed
- docs_163_hard_pass: False（想定内 · fresh_log）

## 次 wave（承認不要）

1. forward P3 向け: セッション経過後に `validate us-forward-returns` 再実行
2. shadow positions 追加 → portfolio P1
3. peer_sync 週次 co-write で log 行数増加を確認
