# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-27

## 3行サマリー
- **週次主系統**: Weekly Candidate Brief — `scripts/run_weekly_candidate_brief.sh`
- P3 live forward usable は **time-dependent monitoring gate**（`matched_normal=1/10` · need 9）— 短期 KPI から外す
- 旧 Weekly Observation Report v1 は主出力ではなく、過去比較/診断/付録として扱う

## §4. ローカル

```text
observation_log: 538
portfolio human: 55% P0-P2
peer_forward: usable
us_forward: 1/10 thin (matched_normal=1; rows_matched may differ)
p3_us_forward_summary: need 9 toward usable
```

## §5. 直近ゲート

| ゲート | 状態 |
| --- | --- |
| `will_be_matchable_after_date_rows` | 16（log 内 · cache 経過で mature） |
| `write_now_count` | 0（ISO 週重複 · L1 ブロック） |
| L1 | **消費済み 2/2** · [skip](../reports/2026-05-26/approved_execution_L1_skip_20260526.md) |
| ISO 週 rollover | `validate forward-p3-status` → `iso_week_rollover` |
| horizon timeline | `p3_horizon_timeline`（#289） |
| path to usable | `validate p3-path-to-usable` / weekly dry-run **P3 path preflight**（#299） |
| P3 CLI hints | `p3_monitoring_next_commands()`（#299） |
| horizon export | `validate p3-horizon-timeline --format json`（#296） |
| matched P3 vs raw | `matched_normal`（dedupe）≠ `rows_matched`（#302–#304） |
| P3 display | forward-p3-status: `all_rows_sample_quality` vs `p3_sample_quality`（#302） |
| L1 rollover passed | `rollover_passed_write_still_blocked` wording（#303） |
| 重複週方針 | [decision](../docs/decisions/2026-05-26_observation_log_duplicate_week_policy.md) |
| portfolio 70% / P3 | usable 到達後に L3 再承認 |

## §6. 監視コマンド

```bash
scripts/run_weekly_candidate_brief.sh
.venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief --format copy --report-date "$(date +%F)" | pbcopy
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate p3-path-to-usable --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate p3-horizon-timeline --format json --horizon-rows 100
.venv/bin/python -m invis_alpha_os.cli.main validate forward-p3-status --format markdown
```

## §7. Weekly Candidate Brief 生成物ポリシー

以下は生成物であり、原則コミットしない。

- `reports/YYYY-MM-DD/weekly_candidate_brief_v0_1.md`
- `reports/YYYY-MM-DD/weekly_candidate_brief_v0_1.json`
- `reports/YYYY-MM-DD/weekly_candidate_brief_copy.md`
- `reports/YYYY-MM-DD/email/*`
- `outputs/operator/weekly_candidate_brief/**`
