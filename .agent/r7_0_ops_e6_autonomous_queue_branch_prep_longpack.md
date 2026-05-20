# R7.0-Ops-E6: autonomous queue branch preparation and overnight trial fix

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。
通常文・表・箇条書きをコードブロック外に分散しないでください。

説明は短く、必要情報だけにしてください。
full diff / full file / full pytest log は出さないでください。
secrets / .env / token / credentials / API key / cache JSON / outputs の中身は出力しないでください。

## 1. State Capsule

- repo: `/Users/uotani/Projects/invest-alpha-os`
- latest main: `c78f8ca`
- Ops-E5 smoke PR #60 merged successfully
- overnight_safe_3h trial result:
  - status: stopped
  - mode: execute
  - tasks: 1/4
  - prs: 0
  - evidence: `outputs/operator/dev_loop/20260520T102654Z/evidence_summary.json`
  - stop_reason: `preflight: branch not pushed to origin: work/r7-0-ops-e-docs-status-microfix`
- interpretation: safety/preflight worked, but regular `autonomous_dev_queue.yaml` tasks need branch preparation/push handling like the smoke queue
- 作業branch: `work/r7-0-ops-e6-autonomous-queue-branch-prep`
- 目的: overnight_safe_3h が通常queueでも安全にPR作成まで進めるよう、task branch preparation / push / preflight を整備する

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

Ops-E5で dev-loop smoke queue はPR作成まで成功した。
一方、通常 `autonomous_dev_queue.yaml` は `branch not pushed to origin` で安全停止した。

必須要件:

1. 通常queue taskにも安全なbranch preparationを追加
   - `prepare_for_pr` / `change_file` / `commit_message` / `branch template` を必要に応じて追加
   - docs/status microfix taskはdocs-only最小差分を作れるようにする
   - 既存smoke queueの成功パターンを再利用する

2. fixed branch再利用を避ける
   - `{run_id}` template または一意branchを使う
   - 例: `work/dev-loop/autonomous/{task_id}/{run_id}`
   - branch名はsanitize

3. preflightを改善
   - branch未pushなら、prepare_for_pr taskでは push まで行う
   - prepare対象外taskなら controlled stop + evidence
   - branch / remote exists / commits ahead / changed files を evidence に残す

4. evidence always written
   - stopped / blocked / completed すべてで `evidence_summary.json` / `dev_loop_result.json` を書く

5. 実行範囲
   - real live HTTP/cache write/Gmail sendなし
   - 自動mergeなし
   - PR作成はgate維持

## 4. 確認対象

- `src/invis_alpha_os/operator/dev_loop.py`
- `src/invis_alpha_os/operator/pr_loop.py`
- `config/tasks/autonomous_dev_queue.yaml`
- `config/tasks/dev_loop_pr_create_smoke_queue.yaml`
- `config/operator_dev_loop_profiles.yaml`
- `tests/test_operator_dev_loop.py`
- `docs/106_r7_0_ops_e2_overnight_run_profile.md`
- `docs/109_r7_0_ops_e4_dev_loop_pr_create_smoke.md`
- `docs/110_r7_0_ops_e5_unique_smoke_branch.md`
- `docs/01_development_status.md`

## 5. テスト要件

最低限、以下をテストする。

1. autonomous queue branch template
   - `{run_id}` / `{task_id}` が一意branchに展開される

2. docs/status microfix prepare
   - docs-only changeを作る
   - commit/push mock success
   - PR作成mock success

3. branch not pushed
   - prepare_for_prありならpushへ進む
   - prepare_for_prなしならcontrolled stop/evidence

4. remote exists
   - force pushしない
   - branch deleteしない
   - evidenceに記録

5. overnight profile dry/execute smoke
   - `overnight_safe_3h` + `max_tasks 1` + `max_prs 1` 相当で通る
   - real GitHub APIはテストで呼ばない

6. existing tests維持

## 6. 実行コマンド目安

必要に応じて調整可。

```bash
git status --short
git rev-parse --short HEAD
git diff --check

.venv/bin/python -m pytest   tests/test_operator_dev_loop.py   tests/test_operator_pr_loop.py   tests/test_operator_runner.py   tests/test_operator_runner_gated.py   tests/test_operator_runner_jquants_wiring.py   -q

.venv/bin/python -m pytest -q
```

real guarded overnight mini trialはPR merge後に人間が実行する。

## 7. docs更新

短く更新する。

- `docs/01_development_status.md`
- 新規docs候補: `docs/111_r7_0_ops_e6_autonomous_queue_branch_prep.md`
- `docs/106` にE6 follow-upを追記

記載内容:

- E5到達点
- overnight_safe_3h trialの停止理由
- E6修正内容
- branch一意化/prepare/push/preflight
- 自動merge禁止維持
- 次のreal guarded trial手順

## 8. PR作成

可能ならPR作成。

PR title候補:

`R7.0-Ops-E6: Prepare autonomous queue branches for overnight trials`

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

- force pushを使いそう
- branch削除を使いそう
- `gh pr merge` / `gh pr close` を呼びそう
- main direct pushしそう
- secrets/token/credentialsを表示しそう
- cache JSON/outputsがcommit対象になりそう
- workflow/Makefile/pyproject変更が必要
- live HTTP/cache write/Gmail sendを呼びそう
- daily/signals defaultを変更しそう
- trading recommendation表現が入りそう
- full testが壊れて原因不明
- branch preparationが無制限/危険になりそう

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
