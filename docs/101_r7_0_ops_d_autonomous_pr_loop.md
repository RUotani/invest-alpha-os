# R7.0-Ops-D — Autonomous PR loop foundation

**日付**: 2026-05-20 · **main 起点**: `134717f` · **性質**: PR draft loop · gated `gh pr create` · no auto-merge

---

## 1. Purpose

task → runner/evidence → tests → git status → PR body draft → optional `gh pr create` の半自律ループ基盤。

**自動 merge は実装しない**（`gh pr merge` 禁止）。

---

## 2. CLI

```bash
# Draft only (default)
alpha-os operator-runner pr-loop --branch work/foo --title "My PR" --dry-run

# Run checks + draft
alpha-os operator-runner pr-loop --branch work/foo --title "My PR" --execute-checks \
  --task config/tasks/r7_0_jquants_ingest_gated_smoke.yaml

# Gated PR create
CONFIRM_GITHUB_PR_CREATE=YES alpha-os operator-runner pr-loop \
  --branch work/foo --title "My PR" --execute-checks --create-pr
```

出力: `outputs/operator/pr_loop/<run_id>/`（`pr_body_draft.md` · evidence JSON）

---

## 3. Gates

| 操作 | 要件 |
|---|---|
| PR draft | 常可（default dry-run） |
| `--execute-checks` | pytest + git status |
| `--create-pr` | `--execute-checks` + `CONFIRM_GITHUB_PR_CREATE=YES` |
| `gh pr merge` | **禁止**（コード上 blocked） |

---

## 4. Boundaries

- CI read-only（本フェーズでは pr-loop 内未統合 · 将来拡張）
- live HTTP / cache write / Gmail send なし
- outputs 未コミット

---

## 5. Verification

```bash
pytest -q tests/test_operator_pr_loop.py tests/test_operator_runner*.py
```
