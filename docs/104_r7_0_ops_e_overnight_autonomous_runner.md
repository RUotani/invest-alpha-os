# R7.0-Ops-E — overnight autonomous development runner

**日付**: 2026-05-20 · **main 起点**: `5155a77` · **性質**: 夜間向けの半自律 dev-loop 追加

---

## 1. Purpose

低リスク task queue を順次処理し、実装チェック・PR作成・CI待機・evidence 記録までを安全に自動化する。

- default は dry-run
- 自動 merge は禁止のまま

---

## 2. CLI

- `alpha-os operator-runner dev-loop`
- `--task-queue config/tasks/autonomous_dev_queue.yaml`
- `--dry-run/--execute-dev-loop`（default dry-run）
- `--create-pr`（既存 `CONFIRM_GITHUB_PR_CREATE=YES` が必要）
- 実行ゲート: `CONFIRM_OPERATOR_DEV_LOOP=YES`
- 制限: `--max-runtime-minutes` / `--max-tasks` / `--max-prs`
- 停止ポリシー: `--stop-on-failure` / `--stop-on-dirty-tree`
- CI待機: `--wait-ci` / `--ci-timeout-seconds` / `--ci-poll-seconds`

---

## 3. Safety

- `pr-loop` を再利用し、`gh pr merge` / `gh pr close` は禁止継続
- dirty tree を監視し、`outputs/`, `.env`, `*cache*.json` が対象なら停止
- failure / blocked / CI timeout など重大条件で停止可能
- live HTTP / cache write / Gmail send / daily-signals default 変更は対象外

---

## 4. Evidence

`outputs/operator/dev_loop/<run_id>/evidence_summary.json` に保存:

- status / mode / stop_reason
- tasks_seen / tasks_executed / prs_created
- taskごとの `pr_url`, `ci_wait_status`, `pr_loop_evidence_path`
- `forbidden_auto_merge: true`

---

## 5. Not done

- 実際のコード生成・編集オーケストレーション（今回は runner 基盤のみ）
- queue taskごとの高度な diff 安全解析
- 朝の human review 連携（通知やダッシュボード）
