# Final Report — Cursor longrun wave 2 (2026-05-26)

<<< COPY FROM HERE >>>

## 結論

**PR #284 merge 済**。L1 weekly 書込に **`--skip-duplicate-iso-week`（opt-in）** と **`p3_weekly_write_plan`**（forward-p3-status）を追加。default behavior は変更なし。P3 usable（1/10→10/10）は依然データ制約（新 ISO 週の初回行が必要）。

確度: **90%**

---

## 時間 / PR

| 項目 | 値 |
| --- | --- |
| Product PR | **#284** squash merge |
| 前回 | #283（P3 summary + preflight） |
| ローカル main | `origin/main` 更新後 `git fetch` 推奨 |

---

## 変更ファイル（#284）

- `us_signal_iso_week_dedupe.py` — ISO week keys, write plan
- `us_signals_batch.py` — skip flag + stats
- `weekly_us_observation.py` / `cli/main.py` — `--skip-duplicate-iso-week`
- `forward_p3_status.py` — `p3_weekly_write_plan`
- `us_forward_p3_stall_diagnosis.py` — `default_watchlist_cache_planned_writes`
- tests + CI fix (`test_us_report_opt_in_operational_readiness.py`)

---

## US forward 停滞への改善

| 改善 | 効果 |
| --- | --- |
| `--skip-duplicate-iso-week` | L1 で **同一週再ログを抑制**（opt-in） |
| `p3_weekly_write_plan` | `write_now` / `skip_duplicate` を JSON/markdown で一覧 |
| preflight 連携 | decision 2026-05-26 方針と整合 |

**次 L1 推奨コマンド**:
```bash
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation \
  --write-observation-log --with-peer-sync --skip-duplicate-iso-week
```

---

## P3 残件

- matched_normal: **1/10** · need: **9**
- `validate forward-p3-status --format json` → `p3_us_forward_summary` / `p3_weekly_write_plan`

---

## テスト

```text
71 passed (product suite)
CI #284: test PASS
```

---

## Safety

| 操作 | 実行 |
| --- | --- |
| live HTTP | **未実行**（本 wave） |
| cache write | **未実行** |
| Gmail | **未実行** |
| observation_log write | **未実行**（product PR のみ） |

---

## 人間承認が必要な残件

1. **L1 残 1 回** — `--skip-duplicate-iso-week` 付きで実行推奨
2. **portfolio 70% / P3** — usable 到達後
3. **STATE.md / batch 証跡** — ローカル未コミット（534行・batch execution docs）

<<< COPY TO HERE >>>
