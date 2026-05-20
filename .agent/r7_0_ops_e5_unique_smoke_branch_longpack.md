# R7.0-Ops-E5: unique branch handling for dev-loop PR-create smoke

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。
通常文・表・箇条書きをコードブロック外に分散しないでください。

説明は短く、必要情報だけにしてください。
full diff / full file / full pytest log は出さないでください。
secrets / .env / token / credentials / API key / cache JSON / outputs の中身は出力しないでください。

## 1. State Capsule

- repo: `/Users/uotani/Projects/invest-alpha-os`
- latest main: `6cbdb9c`
- Ops-E4: PR #58 merged
- real guarded smoke result:
  - status: stopped
  - mode: execute
  - tasks: 1/1
  - prs: 0
  - evidence: `outputs/operator/dev_loop/20260520T101501Z/evidence_summary.json`
  - stop_reason: `task_failed: dev_loop_pr_create_smoke (prepare_failed)`
  - cause: `git push` rejected non-fast-forward for branch `work/r7-0-ops-e4-dev-loop-pr-create-smoke`
- 作業branch: `work/r7-0-ops-e5-unique-smoke-branch`
- 目的: dev-loop PR-create smoke が既存remote branch名の再利用で失敗しないよう、runごとに安全な一意branchを使えるようにする

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

Ops-E4の設計は正しく、evidenceも書けている。
失敗原因は固定branch名の再利用により、remote pushがnon-fast-forward拒否されたこと。

必須要件:

1. smoke branchを一意化する
   - task YAMLまたはdev_loop側で branch template を扱う
   - 候補:
     - `work/r7-0-ops-e4-dev-loop-pr-create-smoke-{run_id}`
     - `work/dev-loop-smoke/{run_id}`
   - run_idは既存の `20260520T101501Z` 形式でよい
   - branch名に使えない文字がないようsanitizeする

2. 既存remote branchがある場合は安全停止
   - force push禁止
   - branch削除禁止
   - non-fast-forward時は controlled stop + evidence
   - 可能ならpush前に `git ls-remote --heads origin <branch>` をread-only確認
   - 既存remote branchありなら新しいbranch名へ切り替えるか、controlled stopする
   - 推奨は一意branch化で衝突回避

3. prepare_for_pr のpreflightを強化
   - current branch / intended branch / base main / ahead count / remote exists を evidenceに記録
   - push failure detailはsanitize
   - push失敗でも evidence_summary.json / dev_loop_result.json は必ず書く

4. smoke queueを更新
   - `config/tasks/dev_loop_pr_create_smoke_queue.yaml`
   - fixed branchではなくtemplateまたはauto branchを使う
   - docs-only変更は継続
   - max_tasks 1 / max_prs 1 想定

5. tests
   - branch template展開
   - remote branch exists時の挙動
   - non-fast-forward failureがcontrolled stop/evidenceになること
   - successful prepare mock path
   - existing tests維持

## 4. 確認対象

- `src/invis_alpha_os/operator/dev_loop.py`
- `src/invis_alpha_os/operator/pr_loop.py`
- `config/tasks/dev_loop_pr_create_smoke_queue.yaml`
- `tests/test_operator_dev_loop.py`
- `docs/109_r7_0_ops_e4_dev_loop_pr_create_smoke.md`
- `docs/01_development_status.md`

既存構造に寄せる。
新規巨大moduleは避ける。

## 5. テスト要件

最低限、以下をテストする。

1. branch template
   - `{run_id}` が一意branch名に展開される

2. smoke queue
   - fixed branch再利用ではなく一意branchを使う

3. remote exists
   - `git ls-remote` mockで既存remote branchを検出
   - force pushしない
   - branch削除しない
   - evidenceに記録

4. push failure
   - non-fast-forward相当のstderrをsanitizeしてevidence記録
   - tracebackなし

5. success path
   - checkout → docs-only変更 → commit → push → PR作成mock
   - auto-mergeなし

6. evidence always written
   - blocked/stopped/completedすべてでjsonあり

## 6. 実行コマンド目安

必要に応じて調整可。

```bash
git status --short
git rev-parse --short HEAD
git diff --check

.venv/bin/python -m pytest   tests/test_operator_dev_loop.py   tests/test_operator_pr_loop.py   tests/test_operator_runner.py   tests/test_operator_runner_gated.py   tests/test_operator_runner_jquants_wiring.py   -q

.venv/bin/python -m pytest -q
```

real guarded smokeはPR merge後に人間が実行する。
このPR内ではmock中心でよい。

## 7. docs更新

短く更新する。

- `docs/01_development_status.md`
- 新規docs候補: `docs/110_r7_0_ops_e5_unique_smoke_branch.md`
- `docs/109` にE5 follow-upを追記

記載内容:

- E4 smoke失敗原因: branch reuse / non-fast-forward
- E5修正: unique branch / branch template
- force push禁止
- branch削除禁止
- evidence always written
- 次のreal guarded smoke手順

## 8. PR作成

可能ならPR作成。

PR title候補:

`R7.0-Ops-E5: Use unique branches for dev-loop PR create smoke`

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
- branch一意化が不安定でPR作成smokeを危険にしそう

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
