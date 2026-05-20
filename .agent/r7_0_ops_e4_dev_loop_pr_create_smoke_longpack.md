# R7.0-Ops-E4: dev-loop driven PR-create smoke

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。
通常文・表・箇条書きをコードブロック外に分散しないでください。

説明は短く、必要情報だけにしてください。
full diff / full file / full pytest log は出さないでください。
secrets / .env / token / credentials / API key / cache JSON / outputs の中身は出力しないでください。

## 1. State Capsule

- repo: `/Users/uotani/Projects/invest-alpha-os`
- latest main: `95c6948`
- Ops-E3: PR #56 merged
- manual PR-create smoke: PR #57 merged successfully
- current gap: manual PR作成は成功したが、dev-loop経由のPR-create smokeは未完成
- 作業branch: `work/r7-0-ops-e4-dev-loop-pr-create-smoke`
- 目的: dev-loop自身が、最小docs-only差分を使って、PR作成gate付きsmokeを安全に完了できるようにする
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

Ops-E4では、夜間runnerの本番前に、dev-loop経由でPR作成まで通す最小smokeを作る。

必須要件:

1. dev-loop PR-create smoke用taskを追加
   - 候補: `config/tasks/dev_loop_pr_create_smoke_queue.yaml`
   - docs-only task
   - 1 task / 1 PR / short runtime
   - 実装差分は最小docsファイルのみ
   - 自動merge禁止

2. dev-loopがPR作成前に有効な差分/commit/branchを持てるようにする
   - 既存構造に合わせて実装
   - 可能ならtaskに `smoke_file` / `change_file` / `commit_message` を持たせる
   - PR作成前に:
     - branchがmain/masterではない
     - branchがoriginへpush済み
     - baseとの差分またはcommitがある
     - working treeが想定内
   - 差分なしならcontrolled stop + evidence

3. evidenceを必ず書く
   - PR作成成功/失敗/差分なし/branch preflight failure すべてで evidence_summary.json と dev_loop_result.json を書く
   - 前回のようにディレクトリだけ作ってjsonなし、を禁止

4. PR作成gateは維持
   - dev-loop実行: `--execute-dev-loop` + `CONFIRM_OPERATOR_DEV_LOOP=YES`
   - PR作成: `--create-pr` + `CONFIRM_GITHUB_PR_CREATE=YES`
   - テストではreal GitHub APIを呼ばない

5. real smoke runbookをdocsに書く
   - 最小コマンド
   - expected result
   - open PR確認
   - CI確認
   - mergeは人間判断

## 4. 確認対象

- `src/invis_alpha_os/operator/dev_loop.py`
- `src/invis_alpha_os/operator/pr_loop.py`
- `src/invis_alpha_os/cli/main.py`
- `config/tasks/autonomous_dev_queue.yaml`
- `config/operator_dev_loop_profiles.yaml`
- `tests/test_operator_dev_loop.py`
- `tests/test_operator_pr_loop.py`
- `docs/106_r7_0_ops_e2_overnight_run_profile.md`
- `docs/107_r7_0_ops_e3_pr_create_failure_handling.md`
- `docs/01_development_status.md`

既存構造に寄せる。
新規巨大moduleは避ける。

## 5. テスト要件

最低限、以下をテストする。

1. smoke queue dry-run
   - docs-only PR作成smoke taskを読み込む
   - plan/evidenceが出る

2. execute gate不足
   - dev-loop gate不足ならblocked

3. PR create gate不足
   - PR作成せずstopped/blocked

4. diffなしbranch
   - controlled stop
   - evidence jsonを書き切る

5. mock PR create success
   - docs-only change/commit/push相当をmock
   - `gh pr create` argv確認
   - auto-mergeしない

6. evidence always written
   - success/failure/blockedすべてで evidence_summary.json / dev_loop_result.json が存在

7. existing tests維持

## 6. 実行コマンド目安

必要に応じて調整可。

```bash
git status --short
git rev-parse --short HEAD
git diff --check

.venv/bin/python -m pytest   tests/test_operator_dev_loop.py   tests/test_operator_pr_loop.py   tests/test_operator_runner.py   tests/test_operator_runner_gated.py   tests/test_operator_runner_jquants_wiring.py   -q

.venv/bin/python -m pytest -q
```

real PR-create smokeを行う場合は、PRを作るだけに留め、自動mergeは禁止。
実行するなら最小queue・max_tasks 1・max_prs 1・明示ゲートあり。

## 7. docs更新

短く更新する。

- `docs/01_development_status.md`
- 新規docs候補: `docs/109_r7_0_ops_e4_dev_loop_pr_create_smoke.md`

記載内容:

- Ops-E4の目的
- dev-loop経由PR作成smoke
- gate条件
- evidence always written
- 自動merge禁止
- smoke実行手順
- 朝の確認項目

## 8. PR作成

可能ならPR作成。

PR title候補:

`R7.0-Ops-E4: Add dev-loop PR create smoke`

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
- evidence jsonを書けない経路が残りそう
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
