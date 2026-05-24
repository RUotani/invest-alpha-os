# Cursor Autonomous Product Development Protocol — invest-alpha-os

## 3行サマリー
- Cursor Agentが Product 実装・PR作成・merge queue・**条件付き squash merge** まで連続実行する。
- **オプション B（2026-05-24 承認）**: ChatGPT が `MERGE` と分類し、CI `SUCCESS` かつ `mergeStateStatus=CLEAN` なら Agent が `gh pr merge --squash` 実行可。
- `REBASE_FIRST` は Agent が rebase 後に再判定。`DO_NOT_MERGE` / live HTTP / cache write / Gmail は禁止のまま。

---

## 0. 目的

```text
Cursor Agent:
- 実装 / テスト / PR / merge queue / handoff
- ChatGPT MERGE + CI green + CLEAN → gh pr merge --squash
- REBASE_FIRST → rebase/retarget → 再チェック → 条件満たせば merge

ChatGPT:
- merge queue の Recommendation 分類

人間:
- オプション B の有効化判断（済）
- live HTTP / cache write / Gmail / portfolio % / RULES.md 改定
```

---

## 1. Cursor Agentへ貼る短文

```markdown
`.agent/cursor_autonomous_product_development_protocol.md` に従い自律開発してください。

merge 条件（オプション B）:
- ChatGPT Recommendation = MERGE（merge queue に記載）
- CI = SUCCESS
- mergeStateStatus = CLEAN
→ `gh pr merge --squash` 実行可

REBASE_FIRST → rebase 後に上記を再確認して merge。
DO_NOT_MERGE / REVIEW_REQUIRED（高リスク）→ merge しない。人間へエスカレーション。

禁止: main直push, force push to main, branch/worktree削除, live HTTP, cache write, Gmail, GitHub auto-merge設定, workflow/Makefile/pyproject変更, operator/増築, daily/signals default変更, outputs/cache/secrets commit。
feature branch への `--force-with-lease` は rebase 後のみ可。
```

---

## 2. Agent merge ゲート（オプション B）

Agent が merge してよい条件（**すべて必須**）:

| # | 条件 |
|---|------|
| 1 | ChatGPT merge queue で当該 PR が **MERGE**（`REBASE_FIRST` 完了後に MERGE 相当なら可） |
| 2 | `gh pr checks` → test **SUCCESS** |
| 3 | `mergeStateStatus` = **CLEAN** |
| 4 | ローカル `pytest -q` full suite **PASS**（merge 直前） |
| 5 | safety grep 問題なし |

Agent が merge **しない**:

```text
DO_NOT_MERGE / SUPERSEDED
REVIEW_REQUIRED（docs-only で .agent/reports 意図確認が必要な場合は merge 前に diff 確認）
live HTTP / cache write / Gmail を含む PR
HIGH risk（RULES 抵触）
```

merge コマンド:

```bash
gh pr merge <N> --squash --delete-branch
```

---

## 3. Merge queue フロー

1. Agent: merge queue 作成（Recommendation = `PENDING_CHATGPT`）
2. ChatGPT: Recommendation 分類
3. Agent: 順序どおり rebase / merge 実行
4. Agent: `reports/YYYY-MM-DD/merge_queue_post_*.md` に結果記録

---

## 4. 許可 / 禁止操作

許可: `gh pr create`, `gh pr checks`, `gh pr merge --squash`（ゲート満たす場合）, rebase, `--force-with-lease` on feature branch

禁止: main push, force push main, auto-merge 設定, ゲート未満の merge

---

## 5. Human approval gates（merge 以外）

```text
live HTTP / cache write / Gmail → 人間明示承認
portfolio [要確認]% → 人間
RULES.md 改定 → 人間
```

---

## 6. 承認履歴

- 2026-05-24: **オプション B** — ユーザー承認。ChatGPT MERGE + CI green + CLEAN で Agent merge 可。

---

End.
