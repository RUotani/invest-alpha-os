# R7.0-Ops-E3: graceful PR-create failure handling for dev-loop

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。
通常文・表・箇条書きをコードブロック外に分散しないでください。

説明は短く、必要情報だけにしてください。
full diff / full file / full pytest log は出さないでください。
secrets / .env / token / credentials / API key / cache JSON / outputs の中身は出力しないでください。

## 1. State Capsule

- repo: `/Users/uotani/Projects/invest-alpha-os`
- latest main: `2ef1412`
- Ops-E2: PR #55 merged
- issue: guarded `--execute-dev-loop --create-pr` smoke failed with traceback
- failure: `RuntimeError: gh pr create failed exit 1`
- observed: `gh pr list --state open --limit 5` returned no open PRs
- 作業branch: `work/r7-0-ops-e3-dev-loop-pr-create-failure-handling`
- 目的: dev-loop / pr-loop が `gh pr create` 失敗時にtracebackで落ちず、stopped + evidenceで安全停止するよう修正する

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

## 3. 今回の修正対象

PR作成つきsmokeで `gh pr create failed exit 1` が発生した。
これは安全上は悪くないが、runnerがtracebackで落ちるのは夜間自走運用に不向き。

必須要件:

1. `gh pr create` 失敗を例外tracebackではなく、controlled stopにする
   - status: `stopped`
   - stop_reason例: `pr_create_failed`
   - evidenceにexit code / sanitized stderr / attempted branchを記録
   - secrets値は含めない

2. dev-loopから見ても安全停止にする
   - task failureとして扱う
   - `--stop-on-failure` なら後続taskを止める
   - evidence_summary.json / dev_loop_result.json に残す

3. no-change / no-commit / invalid branch のpreflightを追加または改善
   - PR作成前に「PRを作れる状態か」を確認できるなら確認
   - 例:
     - branchがmain sync branchではない
     - baseとの差分/commitがある
     - working tree状態が想定内
   - ただし過剰実装は避ける

4. tests
   - `gh pr create` exit 1をmockしてstopped/evidenceを確認
   - tracebackにならないこと
   - auto-merge禁止は維持
   - existing testsを壊さない

5. docs
   - docs/01にOps-E3を短く追記
   - 新規docs候補: `docs/107_r7_0_ops_e3_pr_create_failure_handling.md`

## 4. 確認対象

- `src/invis_alpha_os/operator/pr_loop.py`
- `src/invis_alpha_os/operator/dev_loop.py`
- `src/invis_alpha_os/cli/main.py`
- `tests/test_operator_pr_loop.py`
- `tests/test_operator_dev_loop.py`
- `docs/106_r7_0_ops_e2_overnight_run_profile.md`
- `docs/01_development_status.md`

既存構造に寄せる。
新規巨大moduleは避ける。

## 5. テスト要件

最低限、以下をテストする。

1. pr-loop: gh pr create exit 1
   - tracebackなし
   - status stopped
   - stop_reason `pr_create_failed`
   - evidenceに sanitized failure detail

2. dev-loop: PR作成失敗
   - task failed/stopped扱い
   -後続taskを止める
   - evidenceに記録

3. PR作成gate不足
   - 既存通りPR作成しない

4. PR作成gateあり + mock success
   - 既存通りsuccess

5. auto-merge禁止
   - `gh pr merge` / `gh pr close` を呼ばない

## 6. 実行コマンド目安

必要に応じて調整可。

```bash
git status --short
git rev-parse --short HEAD
git diff --check

.venv/bin/python -m pytest   tests/test_operator_dev_loop.py   tests/test_operator_pr_loop.py   tests/test_operator_runner.py   tests/test_operator_runner_gated.py   tests/test_operator_runner_jquants_wiring.py   -q

.venv/bin/python -m pytest -q
```

可能なら修正後に最小smokeを再試行する。ただしreal PR作成は慎重に。
実PR作成を伴うsmokeを行う場合は、最小task・max-prs 1・明示ゲートあり・自動merge禁止で実行する。

## 7. PR作成

可能ならPR作成。

PR title候補:

`R7.0-Ops-E3: Handle dev-loop PR create failures gracefully`

PR body:

- Summary
- Safety
- Tests
- Evidence
- Not done
- Next action

branch削除は禁止。

## 8. 停止条件

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
- PR作成failure handlingがtracebackを残したままになりそう

## 9. 最終報告フォーマット

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
