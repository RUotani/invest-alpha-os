# Cursor Knowledge — invest-alpha-os Agent-Only Long-Run Operating Playbook

作成日: 2026-06-06 JST  
対象repo: `/Users/uotani/Projects/invest-alpha-os`  
目的: Cursorに毎回バラバラの指示を出さず、開発・PR・CI・merge・Final Reportまで一貫して進めるための常駐知識ファイル。  
プロジェクト: 富豪への道_投資戦略 / invest-alpha-os  
位置づけ: Global Multi-Asset Candidate Discovery OS

---

## 0. 最重要原則

このプロジェクトは **自動売買ボットではない**。

目的は、グローバル複数資産・複数テーマを横断し、候補銘柄・セグメント・テーマを発掘し、根拠・反証・優先度・ポートフォリオ制約をレポートする **Global Multi-Asset Candidate Discovery OS** である。

ただし、v1.1以降、**週次レポートのGmail自動送付は明示承認済み**。

---

## 1. 開発姿勢

### 必ず守ること

```text
- 人間にターミナル操作を何度も要求しない
- Cursorが実装、テスト、PR作成、CI監視、修正、squash merge、main更新まで自律実行する
- Final ReportはMarkdownファイルとして保存する
- チャットへは要点だけ出す
- 既存の未コミット差分がある前提で、最初に境界を固定する
- unrelated changesを混ぜない
- 既存のmanual issue / Gmail生成物 / handoff差分は、今回対象でない限り触らない
```

### やってはいけない進め方

```text
- ユーザーに毎回 gh run list / gh pr checks / git pull を打たせる
- 既に確認済みの情報を再度ユーザーに聞く
- 守りすぎて開発を止める
- proposalだけで終わって実装しない
- 同じ説明やコマンドを何度も分割して投げる
```

---

## 2. 現在の完成状態

### v1.0

```text
- weekly report生成: 完了
- manual issue pack: 完了
- latest README entrypoint: 完了
- operator start here: 完了
- v1-readiness-check: 完了
- weekly-report-user-summary: 完了
```

ユーザーが読む入口:

```text
reports-private/manual_issue/latest/README_FOR_USER.md
```

### v1.1 Gmail送信

```text
- #504: SMTP基盤
- #505: Gmail OAuth実送信
- 2026-06-06 weekly report 実送信済み
- message id: 19e9a26b12d4a2eb
```

送信コマンド:

```bash
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-report-email-send \
  --report-date 2026-06-06 \
  --report-root reports-private/manual_issue/weekly_20260606 \
  --send \
  --format markdown
```

`--auto-env-file` は既定ON。  
`~/.config/invest-alpha-os/daily_gmail.env` を読み込む。

### v1.2 UX改善

```text
- #506 merged (main 756ce5b+)
- guardrail表 / 候補比較 / 深掘りカード / 用語定義
- email renderer / one-page summary 改善
- sample: reports-private/sample_outputs/weekly_report_v1_2_sample.md
```

### v1.3 trial spot send

```text
- trial pack: reports-private/trial_send/weekly_v1_2_2026-06-06/
- Gmail OAuth spot send 実施済み
- message id: 19e9a953c07c3a4a (v1.2 trial)
```

PR作成時は **必ず `--body-file` を使う**（zsh バッククォート問題回避）。

---

## 3. Hard Gates

### 引き続き禁止

```text
- broker API
- trading action / order placement
- actual import
- raw broker Excel direct parsing
- cache write
- live market data fetch
- env / secret display
- unrelated broad feature development
- dependency / pyproject / workflow変更は必要最小限かつ目的明確な場合のみ
```

### 承認済み

```text
- 週次レポートのGmail自動送信
- Gmail OAuth送信
- SMTP送信基盤
- local/launchd経路での週次送信
```

### 注意

```text
- Gmail送信は承認済みだが、secret/tokenの中身をログに出してはいけない
- 送信先はredactする
- テストでは実SMTP/Gmail送信をしない
- mocked send / dry-run / blocked / failed を区別する
```

---

## 4. 作業開始時の標準手順

```bash
cd /Users/uotani/Projects/invest-alpha-os

git status --short
git branch --show-current
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

### 未コミット差分の扱い

`reports-private/`、`handoff/`、manual issue、Gmail送信ログ系の差分があっても、今回対象でなければ触らない。

```text
- 既存未コミット差分は境界として尊重する
- 今回の作業対象ファイルだけstageする
- git add . は原則禁止
- git add はファイル単位で行う
```

### ブランチ作成

```bash
BRANCH=<task-specific-branch>
git checkout -b "$BRANCH"
```

---

## 5. 標準Long-Run実行フロー

Cursorは以下を一連で実行する。

```text
1. RULES.md / STATE.md / 直近decision確認
2. 対象ファイル・既存テスト構造確認
3. 作業境界固定
4. 実装
5. focused tests
6. ruff
7. full pytest
8. 差分確認
9. 対象ファイルだけstage
10. commit
11. push
12. PR作成
13. CI監視
14. CI失敗なら修正してpush
15. green / CLEANならsquash merge
16. main更新
17. Final Report保存
18. チャット要約
```

---

## 6. テスト標準

Python sourceを触った場合:

```bash
env PYTHONPATH=src .venv/bin/python -m pytest -q tests
.venv/bin/ruff check src tests
```

focused testsがある場合:

```bash
env PYTHONPATH=src .venv/bin/python -m pytest -q <focused-test-files>
.venv/bin/ruff check src tests
```

存在しないテストディレクトリを指定して失敗した場合:

```text
- その事実を記録
- 関連する既存テストへ切り替える
- 失敗を隠さない
```

---

## 7. PR作成の標準

### 絶対ルール

`gh pr create --body "..."` は使わない。  
Markdown本文内のバッククォートや `$()` がzshに解釈されるため。

必ず `--body-file` を使う。

### PR作成テンプレ

```bash
cat > /tmp/invest-alpha-os-pr-body.md <<'PRBODY'
## Summary

<what changed>

## Scope

Changed:
- <file or area>

Out of scope:
- workflow changes unless explicitly intended
- Gmail send unless explicitly intended
- live HTTP
- cache write
- actual import
- broker API
- trading action

## Validation

- Focused tests: passed
- Ruff: passed
- Full pytest: passed

## Safety

No broker, trading, import, cache write, live HTTP, or secret display.
PRBODY

gh pr create \
  --base main \
  --head "$(git branch --show-current)" \
  --title "<PR title>" \
  --body-file /tmp/invest-alpha-os-pr-body.md
```

### PRが既に作られているか確認

```bash
gh pr list --head "$(git branch --show-current)" --state all
```

---

## 8. CI監視・merge標準

```bash
PR_NUMBER=$(gh pr list --head "$(git branch --show-current)" --json number --jq '.[0].number')
echo "$PR_NUMBER"

gh pr checks "$PR_NUMBER" --watch
gh pr view "$PR_NUMBER" --json mergeStateStatus,isDraft,reviewDecision,statusCheckRollup
```

green / CLEAN なら:

```bash
gh pr merge "$PR_NUMBER" --squash --delete-branch
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

CI失敗時:

```text
1. failing log確認
2. 原因特定
3. 最小修正
4. focused tests
5. ruff
6. 必要ならfull pytest
7. push
8. CI再監視
```

同一原因で2回失敗した時だけ停止してFinal Report。

---

## 9. Final Report標準

Final Reportは必ずMarkdownファイルに保存する。

推奨保存先:

```text
reports-private/longrun_reports/
```

命名例:

```text
cursor_final_report_YYYYMMDD_<topic>.md
codex_final_report_YYYYMMDD_<topic>.md
```

内容:

```markdown
# Cursor Final Report — <topic>

## 結論

<done / partial / blocked>

## Main State

- latest main:
- completed PR:
- branch:
- worktree:

## Changed Files

- ...

## Validation

- focused tests:
- full tests:
- ruff:
- CI:

## Safety Summary

未実行:
- broker API
- trading action
- actual import
- cache write
- live HTTP
- env/secret display

## Remaining Work

- ...

## Next Action

- ...
```

チャットには全文を貼らない。  
チャットへは以下だけ返す。

```text
- latest main
- completed PR
- changed files
- tests/CI
- user-visible output path
- next action
- safety summary
```

---

## 10. Weekly Report UX改善の知識

### 目的

週次レポートは、投資判断の入口として以下をすぐ読める形にする。

```text
- 今週の結論
- 候補あり/なし
- guardrail
- 深掘り候補
- 見送り条件
- If/Then
- 売買指示ではない明記
```

### 上部に出すべきもの

```text
- 1分結論
- 候補比較表
- guardrail表
- ステータスバッジ
- If/Then
- 次に見るファイル
```

### 上部に出さないもの

```text
- discovery_score
- score_veto_pipeline_source
- internal raw field names
- fixture/internal IDs
- 未説明の英語内部語
```

内部互換のため下部や付録に残すのは可。  
ただし、読者が最初に見る上部は日本語中心にする。

---

## 11. Gmail送信の知識

### 現在の実用経路

```text
local / launchd
  -> run_weekly_candidate_brief.sh
  -> weekly report生成
  -> weekly-report-email-send --send
  -> Gmail OAuth
  -> inbox
```

### 送信確認済み

```text
subject: [invest-alpha-os] Weekly Report 2026-06-06
message id: 19e9a26b12d4a2eb
method: gmail_oauth
```

### 再送コマンド

```bash
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-report-email-send \
  --report-date 2026-06-06 \
  --report-root reports-private/manual_issue/weekly_20260606 \
  --send \
  --format markdown
```

### 状態の区別

```text
generated: レポート生成済み
preview_created: email_preview生成済み
sent: Gmail API/OAuth/SMTPで送信済み
delivered: Gmail inboxで確認済み
blocked: env/secrets不足などで送信せず
failed: 送信試行したが失敗
```

---

## 12. Schedule non-fireの知識

過去に `weekly_candidate_brief.yml` の `event=schedule` が見えなかった。

整理済み:

```text
- #503: schedule non-fire RCA / delivery expectation hardening
- scheduled run未発火はGmail未着の直接原因の一部だった
- ただし現在はlocal/launchd + OAuth送信経路で実用可
```

今後の扱い:

```text
- schedule再観測はread-onlyでよい
- workflow_dispatchをschedule成功の代替証拠にしない
- GitHub Actions側の修正は必要なら別PR
- 実用運用はlaunchd/OAuth経路を優先
```

---

## 13. Cursorが詰まったときの復旧パターン

### PR作成が止まった

原因例:

```text
gh pr create の --body 内バッククォートがzshで解釈された
```

対応:

```bash
killall gh || true

gh pr list --head "$(git branch --show-current)" --state all

cat > /tmp/invest-alpha-os-pr-body.md <<'PRBODY'
<PR body>
PRBODY

gh pr create --base main --head "$(git branch --show-current)" --title "<title>" --body-file /tmp/invest-alpha-os-pr-body.md
```

### unstaged差分が混ざっている

```bash
git status --short
git diff --name-only
git diff --cached --name-only
```

対象だけstage:

```bash
git add <target-file-1> <target-file-2>
```

### reports-private/manual_issueが残る

今回対象でないなら触らない。

```text
untracked/unstagedとして残してよい
Final Reportに「既存境界として未変更」と書く
```

---

## 14. 今後のPR命名例

```text
Improve weekly report UX for v1.2 investment review
Harden weekly report email delivery status taxonomy
Add launchd weekly delivery observation report
Improve candidate deep-dive cards in weekly report
Clarify guardrail-first decision flow
```

---

## 15. ユーザー向け最終要約の型

Cursorは最終的にこれだけ返す。

```markdown
## 結論

<完了 / partial / blocked>

| 項目 | 結果 |
|---|---|
| latest main | `<sha>` |
| completed PR | #xxx |
| tests | focused pass / full pass / ruff pass / CI pass |
| user output | `<path>` |
| hard gate | violation none |

## 次に見るファイル

`<path>`

## 次アクション

<one or two bullets>
```

長文ログは貼らない。

---

## 16. 今後の基本判断

迷ったら以下を優先する。

```text
1. ユーザーがすぐ使えること
2. 人間の手間を減らすこと
3. 生成物を1つの入口へ集約すること
4. CI green / mergeまで自律完了すること
5. 売買・broker・import・secret表示は絶対に触らないこと
```

守りすぎて止まらない。  
危険領域以外は、実装・検証・mergeまで進める。
