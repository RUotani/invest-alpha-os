# Cursor Agent Longpack — Product Architecture + Tree-driven Autonomous Implementation

## 3行サマリー
- Cursor Agentがrepo treeを自分で読んで、投資Product本体の設計・実装・テスト・PR作成まで自走するためのLongpack。
- 人間は高リスク承認・最終merge判断のみ。Terminalコマンドの逐次貼り付けは原則不要。
- live HTTP/cache write/Gmail/main push/force push/auto-merge/Ops増築は禁止。P9/P11後の次Product前進を主目的にする。

---

## 0. Cursor Agentへ貼る短文

```markdown
RULES.md、AGENTS.md、CLAUDE.md、STATE.md、docs/decisions/README.md、docs/decisions/2026-05-23_ssot_introduction.md を読み、このrepoのtreeを自分で調査したうえで、`.agent/cursor_product_architecture_autonomous_longpack.md` に従って作業してください。

人間に追加Terminal作業を求めず、repo tree調査、設計確認、実装、テスト、自己修正、docs/STATE更新、PR作成まで自走してください。

ただし、main merge、live HTTP、cache write、Gmail送信、force push、branch/worktree削除、workflow/Makefile/pyproject変更、operator/増築、auto-mergeは禁止です。
PR作成後に停止し、Final Reportを単一Markdownコードブロックで返してください。
```

---

## 1. このファイルの保存先

```text
.agent/cursor_product_architecture_autonomous_longpack.md
```

---

## 2. 基本判断

この運用は可能。理由:

- SSoTファイル群がmainに揃っている。
- Cursorはrepo treeと既存コードを直接読める。
- 既存PR #215で、P9/P11レベルの実装・テスト・PR化はCursor側で可能と実証済み。
- 人間がやるべきことは「merge判断」と「live/cache/Gmail等の高リスク承認」に絞れる。

ただし、完全自動化してはいけない領域:

- main merge
- live HTTP
- cache write
- Gmail send
- secrets / token
- GitHub auto-merge
- force push
- branch/worktree deletion
- trading recommendation behavior
- daily/signals default behavior
- operator/ new feature

---

## 3. Required SSoT read

作業開始時に必ず読む:

- `RULES.md`
- `AGENTS.md`
- `CLAUDE.md`
- `STATE.md`
- `docs/decisions/README.md`
- `docs/decisions/2026-05-23_ssot_introduction.md`

読み終えたら以下を宣言:

```text
RULES.md と STATE.md を読みました。
```

矛盾を見つけたら作業停止し、矛盾内容を1行で報告。

---

## 4. Repo tree self-inspection

Cursor Agentは、作業前にrepo treeを自分で調査すること。

実行・確認対象:

```bash
git status --short
git branch --show-current
git log --oneline -5
find . -maxdepth 3 -type f | sort | sed 's#^./##' | head -300
find src/invis_alpha_os -maxdepth 4 -type f | sort
find tests -maxdepth 3 -type f | sort
find docs -maxdepth 2 -type f | sort | tail -80
```

人間へコマンド実行を依頼しない。Cursor Agent自身が実行できない場合のみ停止して報告。

---

## 5. Architecture map to build internally

Cursor Agentは、以下を読んで現在構造を把握する。

### Core product areas

```text
src/invis_alpha_os/observation/
src/invis_alpha_os/product/
src/invis_alpha_os/reports/
src/invis_alpha_os/signals/
src/invis_alpha_os/risk/
src/invis_alpha_os/portfolio/
config/
tests/
docs/
```

### Must inspect before coding

```text
src/invis_alpha_os/observation/us_signal_note.py
src/invis_alpha_os/observation/us_signals_batch.py
src/invis_alpha_os/product/us_forward_return_validation.py
src/invis_alpha_os/product/weekly_us_observation.py
src/invis_alpha_os/product/us_universe_expansion.py
src/invis_alpha_os/reports/us_observation_summary.py
src/invis_alpha_os/cli/main.py
tests/test_product_us_forward_return_validation.py
tests/test_product_weekly_us_observation.py
tests/test_us_signal_observation_note.py
tests/test_product_us_universe_expansion.py
STATE.md
docs/147_product_p9_p11_observation_veto_forward_usability.md
```

---

## 6. Product direction after P9/P11

現在の優先は、P9/P11 main反映後のProduct実運用化。

### Priority 1 — P9 operational verification

目的:
- `weekly-us-observation --write-observation-log` の実運用導線を検証。
- observation_logを蓄積した後に `validate us-forward-returns` で sample_quality がどう見えるか確認。
- ただし outputsはcommitしない。

許容:
- dry-run / local output generation
- report clarity improvement
- tests/docs更新

禁止:
- outputs commit
- cache write
- live HTTP
- Gmail send
- default behavior変更

### Priority 2 — peer_sync inventory

目的:
- `signals/peer_sync.py` または関連箇所の現状を棚卸し。
- 未実装なら、最小MVP設計とテスト計画を作る。
- 実装可能なら observation-only helperとして実装。

許容:
- read-only inventory
- product code in `signals/` if narrow and tested
- tests
- docs

禁止:
- operator/追加
- live data依存
- default behavior変更
- trading recommendation wording

### Priority 3 — portfolio observation-only design

目的:
- portfolio / position sizingを直接売買判断にしない形で設計。
- observation-onlyのrisk exposure summaryまたはfuture designに限定。
- 実装は小さく、PRが大きくなりすぎる場合はdocs/designのみ。

### Priority 4 — P10 gated refresh approval pack

目的:
- US30+ tier-1 missing refreshの承認パックを作る。
- 実refreshはしない。
- live HTTP/cache writeは別承認。

許容:
- docs/evidence template
- read-only command examples
- risk checklist

禁止:
- live HTTP
- cache write
- cache JSON commit

---

## 7. Recommended autonomous task selection

Cursor Agentは、tree調査後に最もProduct価値が高いものを1つ選ぶ。

選定優先:

1. peer_sync inventory / MVP if safe
2. P9 operational verification/report hardening
3. P10 gated refresh approval pack read-only
4. portfolio observation-only design

選んではいけないもの:

- operator-runner改修
- new automation framework
- workflow/CI/pre-commit改修
- queue/wave/longrun基盤増築
- STATEだけ更新
- docsだけの水増しPR

---

## 8. Work contract

### Allowed

- `src/invis_alpha_os/signals/`
- `src/invis_alpha_os/risk/`
- `src/invis_alpha_os/portfolio/`
- `src/invis_alpha_os/product/`
- `src/invis_alpha_os/observation/`
- `src/invis_alpha_os/reports/`
- `tests/`
- `docs/`
- `STATE.md`
- `.agent/` run pack or evidence note

### Forbidden

- `operator/` new feature
- `.github/workflows/*`
- `pyproject.toml`
- `Makefile`
- `outputs/**` commit
- cache JSON commit
- `.env`
- secrets
- credentials
- live HTTP/cache write/Gmail
- main direct push
- force push
- branch/worktree deletion
- GitHub auto-merge
- trading recommendation wording

---

## 9. Required implementation workflow

1. Read SSoT.
2. Inspect repo tree.
3. Decide one primary Product target.
4. Write a short plan in `reports/YYYY-MM-DD/<task>_plan.md`.
5. Implement minimally.
6. Add/adjust tests, including failure cases.
7. Run targeted tests.
8. Run full suite.
9. Run safety grep.
10. Update docs/STATE if Product state changed.
11. Create PR if all criteria pass.
12. Stop after PR creation.

Do not ask human to run intermediate commands unless blocked by prohibited actions or credentials.

---

## 10. Test policy

Use:

```bash
.venv/bin/python -m pytest -q
```

For targeted tests, select relevant files based on changed area.

Mandatory expectations:
- full suite must pass before PR
- failure tests must be included for new behavior
- no expectation-only changes to hide a bug
- no live network dependency
- no cache write dependency

---

## 11. Safety grep

Before PR, inspect diff for:

```text
operator/
.github/workflows
pyproject.toml
Makefile
outputs/
cache JSON
.env
token
secret
Gmail
live HTTP
cache write
buy
sell
order
recommendation
```

Allowed phrase:
- `not buy/sell advice`

If unsafe phrase appears outside allowed context, stop and report.

---

## 12. PR rules

Create a PR only if:

- At least one real Product target is improved.
- Full suite passes.
- Diff is limited to allowed files.
- No outputs/cache/secrets.
- No operator/ new feature.
- No default behavior change.
- No live HTTP/cache write/Gmail.
- No trading recommendation wording.
- STATE/docs are consistent.

Do not create a PR if:

- only docs/STATE changed
- only `.agent/` changed
- only P10 read-only without meaningful product readiness
- full suite failed
- safety grep failed
- human action is needed to fix tests

PR body must include:

```markdown
## Summary
## Product value
## Test plan
## Safety
## Review classification
## Follow-up
```

---

## 13. Final Report format

Return one Markdown code block only.

```markdown
## Final Report

### 結論
- status:
- selected task:
- PR:
- human merge required:

### SSoT read
- RULES.md:
- STATE.md:
- decisions:

### Repo/tree inspection
- branch:
- base:
- notable modules inspected:

### Completed product work
-

### Changed files
-

### Tests
- targeted:
- full suite:

### Safety
- operator changes:
- live HTTP/cache write/Gmail:
- outputs/cache/secrets:
- default behavior:
- trading wording:
- workflows/Makefile/pyproject:

### Review classification
- BLOCKER:
- SHOULD_FIX_BEFORE_MERGE:
- NICE_TO_HAVE:
- DEFERRED_OPS_FREEZE:

### Human merge command
```bash
gh pr checks <PR_NUMBER>
gh pr merge <PR_NUMBER> --squash --subject "<subject>"
```

### Next product actions
-
```

---

## 14. Stop conditions

Stop without PR if:

- SSoT conflict
- working tree contains unrelated human changes
- required prohibited operation
- test failure cannot be root-caused safely
- implementation would require live HTTP/cache write
- product behavior risk is unclear
- scope grows beyond one PR
- change drifts into Ops infrastructure

---

## 15. Progress baseline

```text
[Progress]
  signals: 70%  (US cache-only + forward validation + veto-at-t join。peer_sync未完成)
  risk:    55%  (veto-at-t note joinあり。portfolio risk未接続)
  ops:     80%  (十分。追加拡張は凍結)
  data:    60%  (US16稼働。US30+ readinessあり、実refresh未実行)
  ui:      40%  (weekly/daily改善済み。運用UI未完成)
  ---
  投資ロジック稼働までの残作業: 2 件
```

---

End.
