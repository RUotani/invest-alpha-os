# R7.0-Ops-I10 — early completion and completion notification

**日付**: 2026-05-20 · **目的**: productive long-run で実作業完了後に `heartbeat_waiting` だけが続く状態を避け、証跡と通知で終了判断へ寄せる。

---

## 1. 背景（I9 反省）

- 8h run で tasks/PR cap を満たした後も `min_runtime` まで heartbeat のみが続いた。
- 価値は PR 作成までで、残り時間の heartbeat は運用者の待ち時間だけ増やす。

---

## 2. 機構

| 項目 | 説明 |
|---|---|
| `allow_early_completion` | キュー枯渇または cap 到達後、post-phase 入口で early exit |
| evidence | `early_completion_detected`, `early_completion_reason`, `tasks_executed`, `prs_created`, `remaining_runtime_minutes`, `operator_action_required` |
| `completion_notify_enabled` / `--completion-notify` | 完了・early completion・min_runtime 到達時に best-effort 通知（1回） |
| 通知失敗 | run 本体は失敗扱いにしない |

実装: `src/invis_alpha_os/operator/longrun_completion.py` · `dev_loop._run_longrun_post_phase`

---

## 3. プロファイル

| Profile | 用途 |
|---|---|
| `true_longrun_12h` | 耐久試験: `no_early_success_exit` のみ、min_runtime 完走 |
| `true_longrun_12h_bounded` | 本番 productive v2: `allow_early_completion` + `completion_notify_enabled`, `max_prs: 12` |

---

## 4. I10 night 12h v2 開始

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES
bash scripts/run_productive_true_longrun_12h_v2.sh
```

- Queue: `config/tasks/autonomous_dev_queue_productive_12h_v2.yaml`
- Log: `outputs/operator/productive_true_longrun_12h_v2/<run_id>/run.log`
- Evidence: `outputs/operator/dev_loop/<run_id>/evidence_summary.json`

---

## 5. 安全

auto-merge 禁止 · live HTTP / cache write / Gmail / trading 文言禁止 · main 直 push 禁止。
