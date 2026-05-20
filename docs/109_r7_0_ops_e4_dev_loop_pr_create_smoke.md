# R7.0-Ops-E4 — dev-loop PR create smoke

**日付**: 2026-05-20 · **性質**: dev-loop 経由 PR 作成 smoke 用 docs-only マーカー

---

## Purpose

`operator-runner dev-loop` が prepare → commit → push → `gh pr create` まで通す最小 smoke 用の docs-only 差分ファイル。

- 自動 merge 禁止
- 本ファイルへの smoke marker 追記のみ（runner 実行時）

---

## Smoke marker

(dev-loop が実行時に marker 行を追記)

---

## Follow-up (Ops-E5)

- 固定 branch 再利用による non-fast-forward を回避するため、smoke queue は `work/dev-loop-smoke/{run_id}` を使用
- 詳細 **[docs/110](./110_r7_0_ops_e5_unique_smoke_branch.md)**
- dev-loop smoke marker: 20260520T102245Z (2026-05-20T10:22:46Z)
