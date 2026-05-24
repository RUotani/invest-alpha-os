# Cursor Agent Massive Product Longrun Wave Pack — SSoT / UI-light

## 3行サマリー
- Cursor Agentに大量アクションを連続実行させる標準Longpack。人間は高リスク承認・最終merge判断のみ。
- Agentは複数waveで実装・テスト・自己修正・docs/STATE更新・PR作成・merge queue作成まで自走する。
- テスト結果・Final Report・merge queueは、ChatGPTへそのまま貼れるMarkdownファイルまたは単一copy blockで出力する。

---

## 0. Cursor Agentへ貼る短文

```markdown
RULES.md、AGENTS.md、CLAUDE.md、STATE.md、docs/decisions/README.md、docs/decisions/2026-05-23_ssot_introduction.md を読み、`.agent/cursor_massive_product_longrun_wave_pack.md` に従って実行してください。

目的は、Product本体を大量・連続で前進させることです。人間に逐次Terminal作業を求めず、tree調査、実装、テスト、自己修正、docs/STATE更新、PR作成、CI/差分分類、merge queue、ChatGPT貼り付け用レポート作成まで自走してください。

main merge、live HTTP、cache write、Gmail送信、force push、branch/worktree削除、workflow/Makefile/pyproject変更、operator/増築、auto-mergeは禁止です。

すべてのテスト結果とFinal Reportは、ChatGPTへワンクリックで貼れるMarkdownファイル、または単一copy blockで返してください。
```

---

## 1. 保存先

保存パス:

```text
.agent/cursor_massive_product_longrun_wave_pack.md
```

ファイル名:

```text
cursor_massive_product_longrun_wave_pack.md
```

---

## 2. 基本方針

これは「作業時間を埋める」ためのrunではなく、Product本体を前進させるwave executionである。

### 人間がやること

- 高リスク承認
- PR merge判断
- live HTTP/cache write/Gmailなどの明示承認
- portfolio進捗率など人間判断が必要な値の確定

### Cursor Agentがやること

- repo tree調査
- architecture把握
- task選定
- 実装
- テスト追加
- テスト失敗の自己修正
- docs/decision/STATE更新
- PR作成
- PRごとのdiff/safety/CI分類
- ChatGPT貼り付け用レポート作成

---

## 3. 必読SSoT

作業開始時に必ず読む。

- `RULES.md`
- `AGENTS.md`
- `CLAUDE.md`
- `STATE.md`
- `docs/decisions/README.md`
- `docs/decisions/2026-05-23_ssot_introduction.md`

読み終えたら宣言:

```text
RULES.md と STATE.md を読みました。
```

矛盾がある場合は停止。推測で進めない。

---

## 4. 絶対禁止

- main direct push
- force push
- branch deletion
- worktree deletion
- live HTTP
- cache write
- Gmail send
- secrets / `.env` / token output
- daily / signals default behavior change
- `pyproject.toml` change
- `Makefile` change
- `.github/workflows/*` change
- GitHub auto-merge
- `operator/` new feature
- trading recommendation wording
- `outputs/**` commit
- cache JSON commit
- test expectation changes that hide a bug

Allowed safe wording:
- `observation-only`
- `not buy/sell advice`

---

## 5. Wave execution model

Agent may create multiple PRs in one longrun, but must keep them reviewable.

```text
max_prs: 10
max_tasks: 20
continue_until: primary + reserve exhausted or safety stop
```

PR size guideline:

```text
ideal changed files: 3–12
ideal additions: <= 800 where practical
one clear product theme per PR
```

Agent must not merge PRs.  
Human may batch merge multiple PRs only after ChatGPT has reviewed the merge queue.

---

## 6. Product wave queue

### Wave A — peer_sync operationalization

Goal:
- Make peer_sync practically useful in weekly observation/reporting.

Candidate tasks:
1. peer_sync weekly report opt-in polish
2. peer_sync observation_log summary/read-only verification
3. peer_sync status explanations and next actions
4. peer_sync docs examples using current US cache
5. peer_sync failure/insufficient data hardening

### Wave B — observation_log usability

Goal:
- Make weekly observation_log accumulation and validation loop operational.

Candidate tasks:
1. read-only smoke report command or docs
2. observation_log quality summary
3. validation sample growth guidance
4. malformed/legacy row handling tests
5. copy-ready weekly operator report

### Wave C — portfolio observation-only

Goal:
- Move portfolio from `[要確認]%` toward concrete observation-only design.

Candidate tasks:
1. portfolio observation summary improvements
2. exposure/thesis/evidence read-only report
3. docs to define portfolio progress
4. tests for empty/linked/unlinked shadow positions
5. STATE update proposal, but do not invent human-only percentage if uncertain

### Wave D — P10 tier-1 gated refresh approval pack

Goal:
- Prepare approval/evidence pack for tier-1 US cache refresh.

Candidate tasks:
1. read-only refresh checklist
2. evidence template
3. dry-run command guide
4. risk boundary doc
5. post-refresh validation checklist

Forbidden in Wave D:
- live HTTP
- cache write
- cache JSON commit

### Wave E — next signal inventory

Goal:
- Inspect next signals/risk target without Ops expansion.

Candidate tasks:
1. inspect `signals/momentum.py`
2. inspect `signals/peer_sync.py`
3. inspect `risk/veto_rules.py`
4. identify gap vs RULES.md §5
5. implement small observation-only helper only if low-risk and tested

---

## 7. Task selection algorithm

Before coding:

1. Inspect current tree.
2. Read recent docs/STATE/decision.
3. Classify candidate tasks by product value, safety risk, testability, PR size, dependency order.
4. Select tasks in waves.

Selection preference:

```text
1. signals/risk/portfolio actual product behavior
2. observation/report usability that makes product operable
3. data readiness read-only
4. docs/STATE only when attached to product changes
5. never Ops infrastructure unless blocking product work
```

---

## 8. Required workflow per PR

For each PR:

1. Ensure working tree is clean or only contains current task changes.
2. Create or reuse a focused branch.
3. Implement minimal product change.
4. Add failure tests.
5. Run targeted tests.
6. Run full suite.
7. Run safety grep.
8. Update docs/STATE/decision if needed.
9. Create PR.
10. Record PR in merge queue report.
11. Continue to next independent task if safe.

Do not wait for human after each PR unless:
- safety violation
- high-risk approval needed
- full suite cannot be fixed
- branch/merge conflict requires human decision
- product behavior ambiguity

---

## 9. Test policy

Use this form. Do not use bare `pytest`.

```bash
.venv/bin/python -m pytest -q
```

For changed modules, also run targeted tests first.

Every test run must record:
- command
- PASS/FAIL
- number passed
- failed test names
- root cause if failed
- fix if applied
- rerun result

---

## 10. Copy-ready test report rule

Every test report must be saved to:

```text
reports/YYYY-MM-DD/test_report_<task_id>.md
```

Template:

````markdown
<<< COPY FROM HERE >>>
# Test Report — <task_id>

## Summary
- status:
- targeted:
- full suite:
- python:
- branch:
- head:

## Commands
```bash
...
```

## Results
- targeted:
- full suite:

## Failures
- none

## Fixes
- none

## Safety
- operator:
- live HTTP/cache write/Gmail:
- outputs/cache/secrets:
- default behavior:
- workflows/Makefile/pyproject:

<<< COPY TO HERE >>>
````

If returning in chat, use one single Markdown code block, not fragmented logs.

---

## 11. ChatGPT handoff report rule

At the end of every longrun, create:

```text
.agent/product_longrun_handoff_<YYYYMMDD>_<topic>.md
```

Required contents:
- PR list
- merge order
- CI status
- test summary
- changed files by PR
- safety checks
- human-required actions
- error/fix table
- intentionally not executed list
- next recommended wave

Bottom prompt:

```text
ChatGPTへ:
このhandoffを読んで、open PRのmerge可否、merge順、次スプリント優先順位、人間承認が必要な項目だけ判定してください。
Terminal作業は要求せず、GitHub側で確認できる範囲はChatGPTが確認してください。
```

---

## 12. Merge queue report rule

When multiple PRs exist, create:

```text
reports/YYYY-MM-DD/merge_queue_<run_id>.md
```

Required table:

| PR | Title | Branch | CI | Mergeable | Files | Risk | Depends on | Recommendation |
|---|---|---|---|---|---:|---|---|---|

Risk:
- LOW: docs/tests/read-only product, no default change
- MEDIUM: product behavior but opt-in/read-only
- HIGH: live/cache/Gmail/default/risk behavior; must stop

Recommendation:
- MERGE
- REBASE_FIRST
- REVIEW_REQUIRED
- DO_NOT_MERGE
- SUPERSEDED

Agent must not merge. Human can batch merge the `MERGE` rows after ChatGPT review.

---

## 13. Error handling

If tests/build fail:

1. Diagnose root cause.
2. Fix if within allowed scope.
3. Add/adjust test only to reflect correct behavior, not to hide bug.
4. Rerun targeted.
5. Rerun full suite.
6. Record in error table.

Stop and ask human only for:
- prohibited operation
- secrets/credentials
- live HTTP/cache write/Gmail
- risk behavior ambiguity
- workflow/Makefile/pyproject change
- dependency major version change
- repeated failure > 3 cycles
- test expectation masking suspicion

---

## 14. Safety grep

Before each PR and final report, inspect diff for:

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

Allowed safe phrase:
- `not buy/sell advice`

If unsafe phrase appears, stop and report.

---

## 15. PR body template

```markdown
## Summary
-

## Product value
-

## Test plan
- [x] targeted tests:
- [x] full suite:
- [ ] Human merge

## Safety
- No live HTTP/cache write/Gmail
- No default behavior change
- No operator/ expansion
- No outputs/cache/secrets
- No workflow/Makefile/pyproject changes

## Review classification
- FIXED:
- ALREADY_OK:
- DEFERRED_OPS_FREEZE:
- NICE_TO_HAVE:

## Follow-up
-
```

---

## 16. Final Report format

Final Report must be one Markdown code block.

```markdown
<<< COPY FROM HERE >>>
# Final Report — Product Massive Longrun

## Conclusion
- status:
- PRs created:
- PRs ready to merge:
- human action required:

## Main state
- base:
- final branch:
- open PRs:

## PR table
| PR | Title | CI | Mergeable | Risk | Recommendation |
|---|---|---|---|---|---|

## Completed work
-

## Tests
-

## Errors and fixes
| ID | Symptom | Cause | Fix | Result |
|---|---|---|---|---|

## Safety
- operator:
- live HTTP/cache write/Gmail:
- outputs/cache/secrets:
- default behavior:
- trading wording:
- workflows/Makefile/pyproject:

## Human actions
1.
2.

## Next wave
1.
2.
3.

<<< COPY TO HERE >>>
```

---

## 17. Current progress baseline

```text
[Progress]
  signals: 82%  (peer_sync MVP + weekly opt-inあり。次は実運用データ蓄積)
  risk:    62%  (veto-at-t joinあり。portfolio/risk接続は限定)
  ops:     80%  (十分。追加拡張は凍結)
  data:    64%  (US16稼働。US30+ refreshは未実行)
  ui:      45%  (weekly/daily/report改善中)
  ---
  投資ロジック稼働までの残作業: 2 件
```

---

End.
