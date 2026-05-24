# Cursor Agent 開発運用ガイド — Quality / Efficiency / Longrun Standard

## 3行サマリー
- Cursor Agentは、SSoTとrepo treeを自分で読み、Product本体の実装・テスト・自己修正・PR作成・handoff作成までロングランで継続する。
- 人間は承認・merge・live HTTP/cache write/Gmailなどの高リスク判断を担当するため、Agentはその前段の品質保証と効率化を最大限やり切る。
- 目的は「作業量を増やすこと」ではなく、投資シグナル・観測品質・forward validation・portfolio observationを本番観察モードへ近づけること。

---

## 0. Cursor Agentへ貼る短文

```markdown
RULES.md、AGENTS.md、CLAUDE.md、STATE.md、docs/decisions/README.md、docs/decisions/2026-05-23_ssot_introduction.md を読み、このファイル `.agent/cursor_agent_quality_efficiency_longrun_standard.md` に従って開発してください。

あなたは、repo treeを自分で読み、必要なProduct作業を選び、設計・実装・テスト・自己修正・docs/STATE/decision更新・PR作成・merge queue・handoff作成までロングランで自走してください。

人間は承認判断とmerge実行を担当します。あなたは、人間が判断しやすいように、PRごとの品質・安全・CI・依存関係・merge順をMarkdownで整理してください。

禁止:
- main direct push
- force push
- branch/worktree削除
- live HTTP/cache write/Gmail送信の無承認実行
- workflow/Makefile/pyproject変更
- operator/増築
- daily/signals default behavior変更
- outputs/cache/secrets commit
- trading recommendation wording

テスト結果・エラー修正履歴・merge queue・Final Reportは、ChatGPTへそのまま貼れる `<<< COPY FROM HERE >>>` 形式、または `reports/YYYY-MM-DD/*.md` に保存してください。
```

---

## 1. このファイルの保存先

保存パス:

```text
.agent/cursor_agent_quality_efficiency_longrun_standard.md
```

ファイル名:

```text
cursor_agent_quality_efficiency_longrun_standard.md
```

---

## 2. 基本思想

### 人間が担当すること

人間が担当するのは以下だけでよい。

```text
- PRをmergeする / しない
- live HTTPを承認する / しない
- cache writeを承認する / しない
- Gmail送信を承認する / しない
- portfolio進捗%など、人間判断が必要な値を確定する
```

### Cursor Agentが担当すること

Agentは以下を自分で実行する。

```text
- SSoT読込
- repo tree読込
- architecture把握
- 次タスク選定
- 設計メモ作成
- 実装
- テスト追加
- テスト失敗の原因調査
- 自己修正
- full suite
- safety grep
- docs/STATE/decision更新
- PR作成
- merge queue作成
- handoff作成
- ChatGPTに貼れる形式で報告
```

### 最重要方針

```text
人間に逐次Terminal作業を求めない。
Agentが自分で調べ、自分で直し、自分でPR化する。
人間に渡すのは「merge判断に必要な整理済み情報」だけ。
```

---

## 3. 必読SSoT

作業開始時に必ず読む。

```text
RULES.md
AGENTS.md
CLAUDE.md
STATE.md
docs/decisions/README.md
docs/decisions/2026-05-23_ssot_introduction.md
```

読了宣言:

```text
RULES.md と STATE.md を読みました。
```

矛盾がある場合は、作業を止めて1行で報告する。

---

## 4. Repo tree 自動読込

Agentは作業前にrepo treeを自分で確認する。

```bash
git status --short
git branch --show-current
git log --oneline -8
find src/invis_alpha_os -maxdepth 4 -type f | sort
find tests -maxdepth 3 -type f | sort
find docs -maxdepth 2 -type f | sort | tail -120
find .agent -maxdepth 2 -type f | sort || true
```

人間にこのコマンド実行を依頼しない。

---

## 5. 開発優先順位

### 優先する

```text
1. signals / risk / portfolio のProduct本体
2. observation_log / weekly / validation の運用品質
3. forward validation / sample_quality / stale判定
4. portfolio observation-only summary
5. peer_sync / momentum / veto_rules の観測品質
6. P10 refresh の承認前preflightとevidence整備
7. docs/STATE/decision更新。ただしProduct変更に付随する場合のみ
```

### 後回し

```text
- docsだけの水増し
- STATEだけの更新
- handoffだけの更新
- UI装飾のみ
```

### 原則禁止

```text
- operator/増築
- workflow/Makefile/pyproject改修
- automationをさらに自動化するためだけのPR
- daily/signals default behavior変更
- trading recommendation / buy / sell / order文言
```

---

## 6. ロングラン方針

Agentは、1PRごとに止まらず、可能な限りロングランで継続する。

### 目安

```text
max_tasks: 20
max_prs: 10
```

### 継続してよい条件

```text
- working treeが管理できている
- full suiteが通っている
- PR単位のscopeが明確
- 禁止領域に触れていない
- 次タスクがProduct本体に近い
- high-risk承認を必要としない
```

### 停止すべき条件

```text
- live HTTP/cache write/Gmailが必要
- secrets/credentials/envが必要
- risk behaviorが曖昧
- workflow/Makefile/pyproject変更が必要
- operator/に逸れそう
- 同じエラーが3回以上続く
- PRが巨大化してreview不能
- test期待値合わせ疑惑
```

---

## 7. PR粒度

### 理想

```text
1 PR = 1 Product theme
changed files: 3–12程度
additions: 800行以下を目安
full suite pass
docs/STATE/decisionは必要最小限
```

### 許容されるPRタイプ

```text
Product PR:
- 実装 + tests + 必要docs
- 最も望ましい

Read-only readiness PR:
- P10 refresh前提やevidence template
- live/cache実行なし

Docs PR:
- Product PRと分ける明確な理由がある場合のみ

STATE/handoff:
- 単独PRにしない
- Product/docs PRに同梱
```

### 避けるPR

```text
- STATEだけ
- handoffだけ
- docsだけでProduct前進なし
- 複数テーマ混在
- operator/混在
```

---

## 8. テスト標準

### 必須

裸の `pytest` は使わない。

```bash
.venv/bin/python -m pytest -q
```

targeted test後、必ずfull suiteを実行する。

```bash
.venv/bin/python -m pytest -q tests/<target>.py
.venv/bin/python -m pytest -q
```

### テスト失敗時

Agentは以下を自走する。

```text
1. root causeを特定
2. 設計バグか、fixture不備か、期待値ミスか分類
3. 根本原因を修正
4. failure testを追加
5. targeted再実行
6. full suite再実行
7. error/fix tableへ記録
```

禁止:

```text
- テスト期待値だけを変えて隠す
- 失敗テストをskipする
- 根本原因不明のままdocsで逃げる
```

---

## 9. テスト結果の出力形式

すべてのテスト結果は、ChatGPTへそのまま貼れる形にする。

保存先:

```text
reports/YYYY-MM-DD/test_report_<task_id>.md
```

形式:

````markdown
<<< COPY FROM HERE >>>
# Test Report — <task_id>

## Summary
- status:
- branch:
- head:
- python:
- targeted:
- full suite:

## Commands
```bash
.venv/bin/python -m pytest -q tests/...
.venv/bin/python -m pytest -q
```

## Results
- targeted:
- full suite:

## Failures
| Test | Cause | Fix | Rerun |
|---|---|---|---|

## Safety
- operator changes:
- live HTTP/cache write/Gmail:
- outputs/cache/secrets:
- default behavior:
- workflows/Makefile/pyproject:

<<< COPY TO HERE >>>
````

チャットに返す場合も、ログ断片ではなく単一copy blockにする。

---

## 10. Safety grep

PR作成前とFinal Report前に必ず確認。

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

許容される安全文言:

```text
not buy/sell advice
observation-only
```

危険語が出た場合は、文脈を確認し、安全文言でなければ停止。

---

## 11. P10 / live HTTP / cache write の扱い

P10 refreshは、承認があっても即実行しない。

### 実行前preflight

```text
- 対象symbolが明示されている
- live HTTP承認 yes
- cache write承認 yes
- STOOQ_APIKEYなど必要envの存在確認 yes/no
- env値は絶対に出力しない
- no-write live previewが成功
- write対象が想定symbolだけ
- evidence pathが決まっている
```

env不足なら:

```text
BLOCKED_ENV_MISSING
```

として停止。承認済みでも実行しない。

---

## 12. `--strict` smoke の扱い

`exit 2` だけで即失敗扱いしない。

分類:

```text
PASS:
- exit 0

EXPECTED_BLOCKED:
- exit 2だが既知reasonのみ
- docs/STATEで想定済み
- 前回から悪化なし

REGRESSION:
- 新しいreason
- blocker件数増加
- JSONL parse error
- schema invalid
- cache invalid
- unknown failure
```

Agentはreason diffで判断する。

---

## 13. observation_log repeat の扱い

repeatは削除しない。

理由:

```text
repeat signal自体が観測価値を持つ。
raw rowは保持し、summaryで集計する。
```

追加すべきsummary:

```text
repeat_by_symbol
repeat_by_label
first_seen
last_seen
consecutive_weeks
stale_repeat_flag
```

dedupeはraw削除ではなく、report上のgroupingとして扱う。

---

## 14. evidence の扱い

`outputs/evidence` はgit外でよい。  
ただし、handoff依存だけにしない。

repo側に保存するもの:

```text
reports/YYYY-MM-DD/evidence_manifest_<task_id>.md
```

manifestに含める:

```text
- evidence file path
- generated_at
- command
- result
- secretなし確認
- hashまたはsize
- summary
```

evidence本文やcache JSONはcommitしない。

---

## 15. Merge queue

複数PRがある場合は必ず作成。

保存先:

```text
reports/YYYY-MM-DD/merge_queue_<run_id>.md
```

形式:

```markdown
<<< COPY FROM HERE >>>
# Merge Queue — <run_id>

| PR | Title | Base | Head | CI | Mergeable | Files | Risk | Depends on | Agent Recommendation |
|---|---|---|---|---|---|---:|---|---|---|
| #xxx | ... | main | branch | SUCCESS | true | 8 | MEDIUM | none | PENDING_CHATGPT |

## Notes
- Agent must not label MERGE.
- ChatGPT fills MERGE / REBASE_FIRST / REVIEW_REQUIRED / DO_NOT_MERGE / SUPERSEDED.

<<< COPY TO HERE >>>
```

重要:

```text
AgentはMERGE判定を付けない。
AgentはPENDING_CHATGPTまで。
ChatGPTがmerge可否を分類する。
人間はChatGPT判定後にmergeする。
```

---

## 16. Final Report

最終報告は以下のcopy blockで返す。

````markdown
<<< COPY FROM HERE >>>
# Final Report — Cursor Agent Longrun

## Conclusion
- status:
- PRs created:
- PRs ready for ChatGPT review:
- human action required:

## Main state
- base:
- final branch:
- open PRs:

## PR table
| PR | Title | CI | Mergeable | Risk | Depends on | Agent Recommendation |
|---|---|---|---|---|---|---|

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

## Next wave
1.
2.
3.

<<< COPY TO HERE >>>
````

---

## 17. PR body template

```markdown
## Summary
-

## Product value
-

## Test plan
- [x] targeted:
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

## 18. 今日のレビューから追加された注意点

### High

```text
P10承認前にenv preflightが必要。
STOOQ_APIKEY未設定なら承認済みでも実行しない。
```

### High

```text
ops-smoke --strict の exit 2 は reason taxonomy で扱う。
exit codeだけで停止しない。
```

### Medium

```text
observation_log repeatはraw dedupeしない。
summaryでrepeat_count/consecutive_weeksとしてfeature化する。
```

### Medium

```text
outputs/evidenceはgit外でよいが、manifestはrepoへ保存する。
```

### Low

```text
STATE SHA driftは単独PRにしない。
次のProduct/docs PRに同梱する。
```

---

## 19. 次wave候補

承認不要で進めてよい:

```text
1. ops-smoke reason taxonomy
2. evidence manifest
3. observation_log repeat summary
4. portfolio readiness label改善
5. Gmail docs deprecated marker整理
```

人間承認必須:

```text
1. P10 live HTTP/cache write
2. weekly --write-observation-log 実行
3. Gmail本番send
```

---

End.
