# R7.0-Ops-E: overnight autonomous development runner

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。
通常文・表・箇条書きをコードブロック外に分散しないでください。

説明は短く、必要情報だけにしてください。
full diff / full file / full pytest log は出さないでください。
secrets / .env / token / credentials / API key / cache JSON / outputs の中身は出力しないでください。

## 1. State Capsule

- repo: `/Users/uotani/Projects/invest-alpha-os`
- Ops-D3: PR #52 merged後前提
- 作業branch: `work/r7-0-ops-e-overnight-autonomous-runner`
- 目的: 夜間にCursor Agentが複数の低リスク開発タスクをqueue処理し、実装・テスト・PR作成・CI確認・evidence保存まで進め、重大問題時のみ停止する基盤を作る
- 自動mergeは禁止維持

## 2. 絶対禁止

- main direct push
- force push
- branch削除 / worktree削除
- 自動merge
- `gh pr merge`
- `gh pr close`
- secrets / .env / credentials / token 出力
- credentials / token / env commit
- cache JSON commit
- outputs commit
- 無ゲート live HTTP
- 無ゲート cache write
- 無ゲート Gmail send
- daily / signals default変更
- trading recommendation / buy / sell / target price / allocation 表現追加
- portfolio / macro / Veto 接続
- workflow / Makefile / pyproject 変更。必要なら停止して報告

## 3. Ops-Eの完成条件

Ops-Eでは「完全放置の自動merge」ではなく、夜間に安全に走る半自律開発runnerを作る。

完成条件:

1. task queueを読める
   - 候補: `config/tasks/autonomous_dev_queue.yaml`
   - 複数taskを順番に処理
   - taskごとに scope / risk / allowed commands / tests / expected files / stop conditions を持つ

2. `operator-runner dev-loop` を追加
   - default dry-run
   - 実行には `--execute-dev-loop`
   - 追加gate: `CONFIRM_OPERATOR_DEV_LOOP=YES`
   - PR作成には既存ルール通り `--create-pr` + `CONFIRM_GITHUB_PR_CREATE=YES`

3. 夜間運用制限を持つ
   - `--max-runtime-minutes`
   - `--max-tasks`
   - `--max-prs`
   - `--stop-on-failure`
   - `--stop-on-dirty-tree`
   - `--wait-ci`
   - `--ci-timeout-seconds`
   - `--ci-poll-seconds`

4. タスクごとに実行
   - task plan作成
   - 実装指示生成または安全な小変更実行
   - tests実行
   - safety check
   - PR body draft生成
   - optional PR作成
   - optional CI待機
   - evidence保存

5. 重大問題時だけ停止
   - tests fail
   - CI fail / cancelled / timeout
   - secrets検出
   - outputs/cache JSON commit対象
   - forbidden command
   - dirty tree異常
   - live/cache/send/default/trading関連の危険差分
   - merge/closeを呼びそう
   - task scope逸脱

6. 自動merge禁止
   - PR作成まで
   - merge判断は人間が朝に行う

## 4. 初期task queue

最初のqueueは低リスクに限定する。

候補task:

1. docs/status microfix
   - docs/01の状態更新
   - 変更はdocsのみ
   - tests: `git diff --check`

2. runner evidence format polish
   - evidence summaryのキー整理
   - tests: operator runner targeted tests

3. PR loop report template polish
   - PR body / final reportの整形
   - tests: pr_loop tests

4. task queue smoke
   - mock taskのみ
   - tests: new dev_loop tests

実live HTTP/cache write/Gmail sendはOps-E対象外。

## 5. 推奨設計

既存構造に寄せる。

確認対象:

- `src/invis_alpha_os/cli/main.py`
- `src/invis_alpha_os/operator/pr_loop.py`
- `src/invis_alpha_os/operator/runner.py`
- `src/invis_alpha_os/operator/policy.py`
- `src/invis_alpha_os/operator/task_spec.py`
- `tests/test_operator_pr_loop.py`
- `tests/test_operator_runner.py`
- `config/operator_runner_policy.yaml`

候補追加:

- `src/invis_alpha_os/operator/dev_loop.py`
- `config/tasks/autonomous_dev_queue.yaml`
- `tests/test_operator_dev_loop.py`
- `docs/104_r7_0_ops_e_overnight_autonomous_runner.md`

新規巨大moduleは避ける。
既存PR loopを再利用する。

## 6. CLI案

候補:

```bash
alpha-os operator-runner dev-loop   --task-queue config/tasks/autonomous_dev_queue.yaml   --max-runtime-minutes 180   --max-tasks 3   --max-prs 2   --wait-ci   --stop-on-failure
```

実行モード:

- default: dry-run
- `--execute-dev-loop`: task実行
- `CONFIRM_OPERATOR_DEV_LOOP=YES`: 実行gate
- PR作成時のみ:
  - `--create-pr`
  - `CONFIRM_GITHUB_PR_CREATE=YES`

## 7. テスト要件

最低限、以下をテストする。

1. default dry-run
   - queueを読む
   - plan/evidenceのみ
   - 実コマンド/PR作成なし

2. execute gate不足
   - `--execute-dev-loop` ありでも env不足ならblocked

3. execute gateあり
   - mock executorでtaskを順番に実行
   - max-tasksで停止

4. max runtime
   - runtime超過で停止
   - evidenceにreason

5. max prs
   - PR数上限で停止

6. stop on tests fail
   - failureで停止
   - 後続taskを実行しない

7. wait-ci連携
   - Ops-D3のCI waitをmockで利用
   - success/failure/timeout

8. safety
   - forbidden commandを拒否
   - `gh pr merge` / `gh pr close` を呼ばない
   - secrets/output/cache JSON commitなし

## 8. 実行コマンド目安

必要に応じて調整可。

```bash
git status --short
git rev-parse --short HEAD
git diff --check

.venv/bin/python -m pytest   tests/test_operator_dev_loop.py   tests/test_operator_pr_loop.py   tests/test_operator_runner.py   tests/test_operator_runner_gated.py   tests/test_operator_runner_jquants_wiring.py   -q

.venv/bin/python -m pytest -q
```

`tests/test_operator_dev_loop.py` がまだ存在しない場合は新規作成する。

## 9. docs更新

短く更新する。

- `docs/01_development_status.md`
- 新規docs: `docs/104_r7_0_ops_e_overnight_autonomous_runner.md`

記載内容:

- Ops-Eの目的
- 夜間自走の範囲
- default dry-run
- execution gate
- PR作成gate
- CI wait
- stop conditions
- 自動merge禁止
- live/cache/send/default/trading禁止
- 次フェーズ候補

## 10. PR作成

可能ならPR作成。

PR title候補:

`R7.0-Ops-E: Add overnight autonomous development runner`

PR body:

- Summary
- Safety
- Tests
- Evidence
- Not done
- Next action

branch削除は禁止。

## 11. 停止条件

以下なら即停止。

- `gh pr merge` / `gh pr close` を呼びそう
- main direct pushしそう
- force pushしそう
- branch/worktree削除しそう
- secrets/token/credentialsを表示しそう
- cache JSON/outputsがcommit対象になりそう
- workflow/Makefile/pyproject変更が必要
- live HTTP/cache write/Gmail sendを呼びそう
- daily/signals defaultを変更しそう
- trading recommendation表現が入りそう
- full testが壊れて原因不明
- 夜間runnerが無制限ループになりそう

## 12. 最終報告フォーマット

単一Markdownコードブロックで返す。

含める項目:

- branch
- start main
- commit
- PR URL
- changed files概要
- 実装概要
- safety確認
- tests結果
- evidence path
- 未実施事項
- 次アクション
