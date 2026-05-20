# R7.0-Ops-D: autonomous PR loop foundation

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。
通常文・表・箇条書きをコードブロック外に分散しないでください。

説明は短く、必要情報だけにしてください。
full diff / full file / full pytest log は出さないでください。
secrets / .env / token / credentials / API key / cache JSON / outputs の中身は出力しないでください。

## 1. State Capsule

- repo: `/Users/uotani/Projects/invest-alpha-os`
- Ops-A: PR #46 merged
- Ops-B: PR #47 merged, main `e23d9fb`
- Ops-C: PR #48 merged後前提
- 作業branch: `work/r7-0-ops-d-autonomous-pr-loop`
- 目的: task → runner/evidence → tests → PR作成 までの半自律ループ基盤を作る
- 重要: 自動mergeはまだ実装しない

## 2. 絶対禁止

- main direct push
- force push
- branch削除 / worktree削除
- 自動merge
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

Ops-Dでは「自律PRループの土台」を作る。

やること:

1. operator-runnerまたは新規operator commandで、次の流れをdry-run中心に管理できるようにする
   - task spec読み込み
   - runner実行
   - evidence確認
   - tests command実行
   - git status確認
   - PR body draft生成
   - optionalで `gh pr create` 実行

2. defaultはdry-run
   - GitHub PR作成はデフォルトではしない
   - PR作成には明示フラグ必須
   - 候補: `--create-pr`
   - さらに gate: `CONFIRM_GITHUB_PR_CREATE=YES`

3. 自動mergeは禁止
   - `gh pr merge` は絶対に呼ばない
   - mergeは人間/別Longpack判断

4. PR body draft
   - Summary
   - Safety
   - Tests
   - Evidence
   - Not done
   - Next action
   - Final report single markdown code block rule

5. CI監視はread-onlyまで
   - `gh pr checks` / `gh run list` は可
   - ただし自動mergeしない
   - CI failならstop/evidence

6. evidence
   - outputs配下にPR loop evidenceを生成
   - commit禁止
   - secretsなし

## 4. 推奨設計

既存構造に寄せる。

確認対象:

- `src/invis_alpha_os/cli/main.py`
- `src/invis_alpha_os/operator/runner.py`
- `src/invis_alpha_os/operator/policy.py`
- `src/invis_alpha_os/operator/task_spec.py`
- Ops-A/B/C tests
- `config/operator_runner_policy.yaml`

候補実装:

- CLI: `operator-runner pr-loop`
  または
- CLI: `operator-runner run --pr-loop`

既存設計に自然な方を選ぶ。

新規巨大moduleは避ける。
小さく実装する。

## 5. 安全ゲート

PR作成には両方必須:

- CLI flag: `--create-pr`
- env: `CONFIRM_GITHUB_PR_CREATE=YES`

不足時:

- PR body draftのみ作成
- `gh pr create` は呼ばない
- evidenceに blocked/draft_only を記録

禁止:

- `gh pr merge`
- `gh pr close`
- branch delete
- force push

## 6. テスト要件

最低限、以下をテストする。

1. default dry-run
   - PR body draftのみ
   - `gh pr create` 未実行

2. `--create-pr` あり but gate不足
   - blocked
   - `gh pr create` 未実行

3. `--create-pr` + gateあり
   - mock subprocessで `gh pr create` argv確認
   - real GitHub APIは呼ばない

4. CI read-only check
   - mockでpass/fail両方
   - fail時stop/evidence

5. 自動merge禁止
   - どの経路でも `gh pr merge` が呼ばれないこと

6. safety
   - secrets/output/cache JSON commitなし
   - forbidden termsなし
   - trading recommendationなし

## 7. 実行コマンド目安

必要に応じて調整可。

```bash
git status --short
git rev-parse --short HEAD
git diff --check

.venv/bin/python -m pytest \
  tests/test_operator_runner*.py \
  -q

.venv/bin/python -m pytest -q
```
