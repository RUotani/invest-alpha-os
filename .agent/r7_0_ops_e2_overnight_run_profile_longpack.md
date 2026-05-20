# R7.0-Ops-E2: overnight run profile and PR-create gated smoke

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。
通常文・表・箇条書きをコードブロック外に分散しないでください。

説明は短く、必要情報だけにしてください。
full diff / full file / full pytest log は出さないでください。
secrets / .env / token / credentials / API key / cache JSON / outputs の中身は出力しないでください。

## 1. State Capsule

- repo: `/Users/uotani/Projects/invest-alpha-os`
- latest main: `5fdf040`
- Ops-E1: PR #54 merged
- guarded execute smoke: `mode=execute tasks=1/4 prs=0`, `stop_reason=max_tasks reached: 1`
- 作業branch: `work/r7-0-ops-e2-overnight-run-profile`
- 目的: 夜間運用に向け、dev-loopの長時間実行プロファイル、PR作成ゲート付きsmoke、runbook/evidenceを整備する
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

## 3. 今回の実装範囲

Ops-E2では「今夜走らせても安全な形」に近づける。
ただし自動mergeはまだ禁止。

必須要件:

1. overnight run profileを追加
   - config候補: `config/operator_dev_loop_profiles.yaml`
   - profile例:
     - `smoke_20min`
     - `overnight_safe_3h`
     - `overnight_safe_6h`
   - 各profileに以下を持たせる:
     - max_runtime_minutes
     - max_tasks
     - max_prs
     - wait_ci
     - ci_timeout_seconds
     - ci_poll_seconds
     - stop_on_failure
     - stop_on_dirty_tree

2. CLIにprofile指定を追加
   - 候補: `operator-runner dev-loop --profile overnight_safe_3h`
   - 明示CLI引数がある場合はprofile値をoverrideできる
   - defaultは従来挙動を壊さない

3. PR作成gate付きsmokeを整備
   - PR作成には既存通り:
     - `--create-pr`
     - `CONFIRM_GITHUB_PR_CREATE=YES`
   - dev-loop実行には:
     - `--execute-dev-loop`
     - `CONFIRM_OPERATOR_DEV_LOOP=YES`
   - テストではreal GitHub APIを呼ばない
   - 実smokeでは最小task/最大PR 1で止める

4. night-run runbookを追加
   - docs候補: `docs/106_r7_0_ops_e2_overnight_run_profile.md`
   - Terminalに貼るコマンドを明記
   - ただし secrets/token/env は出さない
   - 朝の確認項目:
     - evidence path
     - PR一覧
     - CI結果
     - git status
     - stopped reason
     - mergeは人間判断

5. evidence強化
   - profile名
   - effective limits
   - PR作成gate status
   - run start/end
   - final stop reason
   - processed tasks
   - created PR count

## 4. 確認対象

- `src/invis_alpha_os/operator/dev_loop.py`
- `src/invis_alpha_os/operator/pr_loop.py`
- `src/invis_alpha_os/cli/main.py`
- `config/tasks/autonomous_dev_queue.yaml`
- `tests/test_operator_dev_loop.py`
- `docs/104_r7_0_ops_e_overnight_autonomous_runner.md`
- `docs/105_r7_0_ops_e1_dev_loop_safety_validators.md`
- `docs/01_development_status.md`

既存構造に寄せる。
新規巨大moduleは避ける。

## 5. テスト要件

最低限、以下をテストする。

1. profile load
   - `smoke_20min` を読める
   - effective limitsがevidenceに出る

2. profile override
   - CLI引数でprofile値を上書きできる

3. default互換
   - profile未指定なら従来挙動

4. PR create gate不足
   - `--create-pr` ありでも env不足ならPR作成しない

5. PR create gateあり
   - mockで `gh pr create` argv確認
   - real GitHub APIは呼ばない

6. overnight profile safety
   - max_runtime/max_tasks/max_prs が効く
   - auto-merge禁止

7. dry-run/execute smoke互換
   - 既存dev-loop testsを壊さない

## 6. 実行コマンド目安

必要に応じて調整可。

```bash
git status --short
git rev-parse --short HEAD
git diff --check

.venv/bin/python -m pytest   tests/test_operator_dev_loop.py   tests/test_operator_pr_loop.py   tests/test_operator_runner.py   tests/test_operator_runner_gated.py   tests/test_operator_runner_jquants_wiring.py   -q

.venv/bin/python -m pytest -q

.venv/bin/python -m invis_alpha_os.cli.main operator-runner dev-loop   --task-queue config/tasks/autonomous_dev_queue.yaml   --profile smoke_20min   --max-tasks 1   --max-prs 1   --stop-on-failure   --stop-on-dirty-tree
```

## 7. docs更新

短く更新する。

- `docs/01_development_status.md`
- 新規docs: `docs/106_r7_0_ops_e2_overnight_run_profile.md`

記載内容:

- Ops-E2の目的
- profile一覧
- guarded execute smoke手順
- PR作成gate
- overnight safe run手順
- 朝の確認手順
- 自動merge禁止
- live/cache/send/default/trading禁止

## 8. PR作成

可能ならPR作成。

PR title候補:

`R7.0-Ops-E2: Add overnight dev-loop run profiles`

PR body:

- Summary
- Safety
- Tests
- Evidence
- Not done
- Next action

branch削除は禁止。

## 9. 停止条件

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
- profileが無制限実行になりそう
- PR作成がgateなしで走りそう

## 10. 最終報告フォーマット

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
