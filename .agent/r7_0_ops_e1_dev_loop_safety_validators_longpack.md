# R7.0-Ops-E1: dev-loop safety validators

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。
通常文・表・箇条書きをコードブロック外に分散しないでください。

説明は短く、必要情報だけにしてください。
full diff / full file / full pytest log は出さないでください。
secrets / .env / token / credentials / API key / cache JSON / outputs の中身は出力しないでください。

## 1. State Capsule

- repo: `/Users/uotani/Projects/invest-alpha-os`
- latest main: `8ee1676`
- Ops-E: PR #53 merged
- Ops-E dry-run smoke: `tasks=2/4`, `stop_reason=max_tasks reached: 2`
- 作業branch: `work/r7-0-ops-e1-dev-loop-safety-validators`
- 目的: 夜間dev-loopを実行モードへ近づける前に、scope逸脱・危険差分・禁止コマンド・commit対象を検査する安全バリデータを追加する

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

Ops-E1では、`operator-runner dev-loop` に安全バリデータを追加する。

必須要件:

1. taskごとの変更scope検査
   - task YAMLに `allowed_paths` / `forbidden_paths` / `risk_level` のような設定を追加候補にする
   - 許可外ファイル変更があればstop/evidence
   - docs-only taskでsrc変更があればstop
   - code taskでworkflow/Makefile/pyproject変更があればstop

2. dirty tree検査の強化
   - `outputs/`
   - `.env`
   - token / credentials / secret
   - cache JSON
   - これらがgit statusに出たらstop
   - ただし未追跡outputsはcommit対象にしない設計なら、検出・報告のみかstopかを既存方針に合わせる

3. forbidden command検査
   - `gh pr merge`
   - `gh pr close`
   - `git push --force`
   - `git branch -D`
   - `git worktree remove`
   - live/cache/send系の無ゲート実行
   - 検出時はstop/evidence

4. forbidden text検査
   - buy / sell / target price / allocation / trading recommendation
   - portfolio / macro / Veto 接続
   - 投資助言に見える文言がrunner出力・PR body・docsに紛れないようにする
   - 既存文脈でテスト名等に含まれる場合はfalse positiveを避ける

5. evidence強化
   - `safety_validator_status`
   - `scope_violations`
   - `dirty_tree_violations`
   - `forbidden_command_violations`
   - `forbidden_text_violations`
   - `checked_paths`

6. default dry-run維持
   - 実行モードはまだ慎重
   - 今回もreal overnight executeはしない

## 4. 確認対象

- `src/invis_alpha_os/operator/dev_loop.py`
- `src/invis_alpha_os/operator/pr_loop.py`
- `src/invis_alpha_os/operator/policy.py`
- `src/invis_alpha_os/operator/task_spec.py`
- `config/tasks/autonomous_dev_queue.yaml`
- `tests/test_operator_dev_loop.py`
- `docs/104_r7_0_ops_e_overnight_autonomous_runner.md`
- `docs/01_development_status.md`

既存構造に寄せる。
新規巨大moduleは避ける。

## 5. テスト要件

最低限、以下をテストする。

1. allowed_paths正常
   - docs taskでdocsのみ変更ならpass

2. allowed_paths違反
   - docs taskでsrc変更ならstop

3. forbidden_paths違反
   - workflow / Makefile / pyproject 変更ならstop

4. dirty tree違反
   - `.env` / token / credentials / cache JSON / outputs commit対象を検出

5. forbidden command
   - `gh pr merge` / `gh pr close` / force push / branch deleteを拒否

6. forbidden text
   - buy/sell/target price/allocation/trading recommendation を検出
   - false positiveは必要最小限に抑える

7. dev-loop dry-run互換
   - 既存dry-run smokeが壊れない
   - `tasks=2/4` 相当の計画処理が継続

## 6. 実行コマンド目安

必要に応じて調整可。

```bash
git status --short
git rev-parse --short HEAD
git diff --check

.venv/bin/python -m pytest   tests/test_operator_dev_loop.py   tests/test_operator_pr_loop.py   tests/test_operator_runner.py   tests/test_operator_runner_gated.py   tests/test_operator_runner_jquants_wiring.py   -q

.venv/bin/python -m pytest -q

.venv/bin/python -m invis_alpha_os.cli.main operator-runner dev-loop   --task-queue config/tasks/autonomous_dev_queue.yaml   --max-runtime-minutes 30   --max-tasks 2   --max-prs 1   --stop-on-failure   --stop-on-dirty-tree
```

## 7. docs更新

短く更新する。

- `docs/01_development_status.md`
- 新規docs: `docs/105_r7_0_ops_e1_dev_loop_safety_validators.md`

記載内容:

- Ops-E1の目的
- safety validator項目
- scope検査
- forbidden command/text検査
- dirty tree検査
- default dry-run維持
- 次フェーズ: guarded execute-dev-loop smoke

## 8. PR作成

可能ならPR作成。

PR title候補:

`R7.0-Ops-E1: Add dev-loop safety validators`

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
- safety validatorが過剰にfalse positiveを起こし既存運用を壊しそう

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
