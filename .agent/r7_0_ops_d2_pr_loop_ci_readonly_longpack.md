# R7.0-Ops-D2: PR loop CI read-only integration

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。
通常文・表・箇条書きをコードブロック外に分散しないでください。

説明は短く、必要情報だけにしてください。
full diff / full file / full pytest log は出さないでください。
secrets / .env / token / credentials / API key / cache JSON / outputs の中身は出力しないでください。

## 1. State Capsule

- repo: `/Users/uotani/Projects/invest-alpha-os`
- latest main: `6e3cbad`
- Ops-D: PR #49 merged
- Ops-D longpack recovery: PR #50 merged
- 作業branch: `work/r7-0-ops-d2-pr-loop-ci-readonly`
- 目的: autonomous PR loop に optional read-only CI check を追加する
- 重要: 自動mergeは引き続き禁止

## 2. 絶対禁止

- main direct push
- force push
- branch削除 / worktree削除
- 自動merge
- `gh pr merge` 実行
- `gh pr close` 実行
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

Ops-Dで作った autonomous PR loop foundation に、read-only CI check を追加する。

必須要件:

1. optional CI check
   - PR作成後、または既存PR指定時に `gh pr checks` 相当をread-onlyで確認できる
   - 候補flag: `--check-ci`
   - PR番号指定が既存設計にあるならそれを使う
   - なければ最小追加で自然な設計にする

2. read-only限定
   - `gh pr checks` / `gh run list` は許可
   - `gh pr merge` は絶対禁止
   - `gh pr close` も禁止
   - CI fail/pending時は stop/evidence

3. evidence
   - CI status を evidence に記録
   - success / pending / failing / cancelled / unknown を区別
   - fail/pending時に次アクションが分かること
   - secretsなし

4. mock tests
   - real GitHub API はテストで呼ばない
   - subprocess/mockで argv と戻り値を確認

## 4. 実装確認対象

まず以下を確認する。

- `src/invis_alpha_os/cli/main.py`
- `src/invis_alpha_os/operator/pr_loop.py` または同等module
- `src/invis_alpha_os/operator/runner.py`
- `src/invis_alpha_os/operator/policy.py`
- `tests/test_operator_runner*.py`
- Ops-Dのテストファイル
- `docs/01_development_status.md`

既存構造に寄せる。
新規巨大moduleは避ける。
小さく実装する。

## 5. テスト要件

最低限、以下をテストする。

1. default
   - CI checkは実行されない
   - 既存挙動維持

2. `--check-ci`
   - mockで `gh pr checks` argv確認
   - real GitHub APIは呼ばない

3. CI success
   - status success
   - stopしない
   - evidenceにsuccess記録

4. CI pending/fail
   - stopまたはblocked
   - evidenceにreason記録
   - auto-mergeなし

5. 自動merge禁止
   - どの経路でも `gh pr merge` が呼ばれないこと

6. safety
   - outputs/cache JSON/secrets/env/tokenがcommit対象にない
   - forbidden termsなし
   - trading recommendationなし

## 6. 実行コマンド目安

必要に応じて調整可。

```bash
git status --short
git rev-parse --short HEAD
git diff --check

.venv/bin/python -m pytest   tests/test_operator_runner*.py   -q

.venv/bin/python -m pytest -q
```

## 7. docs更新

短く更新する。

- `docs/01_development_status.md`
- 新規docs候補: `docs/102_r7_0_ops_d2_pr_loop_ci_readonly.md`

記載内容:

- Ops-D2の目的
- CI確認はread-only
- defaultではCI確認しない
- `--check-ci` などの明示flag
- success/fail/pendingのevidence
- 自動merge禁止
- 次フェーズ候補

## 8. PR作成

可能ならPR作成。

PR title候補:

`R7.0-Ops-D2: Add read-only CI checks to PR loop`

PR body:

- Summary
- Safety
- Tests
- Evidence
- Not done

branch削除は禁止。

## 9. 停止条件

以下なら即停止。

- `gh pr merge` を呼びそう
- `gh pr close` を呼びそう
- main direct pushしそう
- force pushしそう
- branch/worktree削除しそう
- secrets/token/credentialsを表示しそう
- cache JSON/outputsがcommit対象になりそう
- workflow/Makefile/pyproject変更が必要
- real GitHub APIがテストでmockなしに呼ばれそう
- full testが壊れて原因不明

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
