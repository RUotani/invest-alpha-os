# R7.0-Ops-E1 — dev-loop safety validators

**日付**: 2026-05-20 · **main 起点**: `8ee1676` · **性質**: Ops-E safety validator 強化

---

## 1. Purpose

`operator-runner dev-loop` を execute mode に近づける前に、scope逸脱・危険差分・禁止コマンド・禁止文言を検出して停止できるようにする。

---

## 2. Added validators

- scope validator: taskごとの `allowed_paths` / `forbidden_paths` を検査
- dirty tree validator: `outputs/`, `.env`, token/credentials/secret, cache JSON を検出
- forbidden command validator: `gh pr merge`, `gh pr close`, force push, branch/worktree delete を検出
- forbidden text validator: `buy/sell/target price/allocation/trading recommendation` を検出

---

## 3. Evidence fields

`outputs/operator/dev_loop/<run_id>/evidence_summary.json` に追加:

- `safety_validator_status`
- `scope_violations`
- `dirty_tree_violations`
- `forbidden_command_violations`
- `forbidden_text_violations`
- `checked_paths`

---

## 4. Safety posture

- default dry-run は維持
- auto-merge 禁止は維持
- live/cache/send/default/trading の危険系は validator と既存ガードで停止

---

## 5. Next phase

guarded `--execute-dev-loop` smoke を小さな queue で実施し、false positive / false negative を確認する。
