# R7.0-Ops-I — productive 8h autonomous task queue

**日付**: 2026-05-21 · **性質**: 実開発向け 16 task キュー + preflight

---

## 1. Problem

- `true_longrun_8h` は 8h 未満で止まらない（infrastructure）
- 既存 `autonomous_dev_queue_longrun.yaml` は ~6 docs marker → 早く cap/queue 枯渇 → heartbeat のみ

---

## 2. Two modes

| モード | コマンド | 目的 |
|---|---|---|
| Infrastructure | `bash scripts/run_true_longrun_8h.sh` | 8h ランタイム検証 |
| **Productive** | `bash scripts/run_productive_true_longrun_8h.sh` | 15 task で PR 生成を最大化 |

---

## 3. Queue

`config/tasks/autonomous_dev_queue_productive_8h.yaml` — 16 tasks（operator / long-run / discovery / daily-gmail docs）

---

## 4. Preflight

起動時に表示（失敗しない）:

```text
productive-longrun preflight: tasks=15 preparable=15 max_tasks=100 max_prs=10 min_runtime=480m note=queue may exhaust before min_runtime; runner will heartbeat after exhaustion
```

---

## 5. Safety

- live HTTP / cache write / Gmail send / default 変更なし
- auto-merge 禁止

---

## 6. Expected success

- `stop_reason=min_runtime reached: 480`（queue 枯渇後は heartbeat 継続）

(dev-loop marker 追記用スタブ)
- dev-loop smoke marker: 20260521T133654Z (2026-05-21T13:36:55Z)
- dev-loop smoke marker: 20260521T140219Z (2026-05-21T14:02:20Z)
- dev-loop smoke marker: 20260521T223933Z (2026-05-21T22:40:49Z)
