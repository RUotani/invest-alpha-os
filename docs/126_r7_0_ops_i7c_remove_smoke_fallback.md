# R7.0-Ops-I7C — Remove runtime smoke fallback from productive dev-loop

**日付**: 2026-05-22 · **性質**: v2 run が `docs/smoke.md` quarantine で tasks=0/32 停止

---

## 1. What happened

- I7B マージ後、外側 preflight の `git status` は空でも dev-loop 開始直後に停止
- `stop_reason=forbidden quarantine dirty path: docs/smoke.md`（run `20260522T131716Z`）
- v2 queue は全 task に明示 `change_file` あり。原因は **作業ツリー上の quarantine 残骸** と、productive で `smoke_file` 暗黙フォールバックを許す余地

---

## 2. Fix

1. productive queue 読込時に `productive_queue_prepare_violations` — `prepare_for_pr` は YAML 明示 `change_file` 必須
2. `productive_quarantine_repo_violations` — 実行前に `docs/smoke.md` の存在/dirty を拒否
3. `_resolve_prepare_change_file` — `docs/smoke.md` への暗黙フォールバック禁止、専用 marker path のみ
4. productive prepare は task 専用ヘッダ（`# Dev-loop marker: <task_id>`）

---

## 3. Next action

1. Merge I7C PR
2. `docs/smoke.md` を repo 外へ退避し clean tree を確認
3. v2 12h を `autonomous_dev_queue_productive_12h_v2.yaml` で再開
