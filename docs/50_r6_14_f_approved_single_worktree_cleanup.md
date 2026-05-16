# R6.14-F — Approved single old R6.12 worktree cleanup

**ステータス**: 作業ブランチ `work/r6-14-f-approved-single-worktree-cleanup` のみ（**`main` 未反映**）。**実施したのは、承認条件を満たす単一 **`invest-alpha-os-r6-12-*` worktree** に対する `git worktree remove` のみ（1 回）** — **`rm -rf`・local/remote branch 削除・他 path の削除は行っていない**。

---

## 1. 目的

- 古い **R6.12** 系 worktree のうち、`main` に **既に統合済み**で **`git merge-base --is-ancestor` が真**であり、かつ **`git status` が clean** な **1 本だけ** を `git worktree remove` で解除する。

## 2. 非目的

- **`/Users/uotani/Projects/invest-alpha-os-r6-12-f` 以外**の worktree 削除（**本実行では他 0 本**）。
- **local / remote branch 削除**（`work/r6-12-f-us-report-opt-in-hardening-design` は **残存し得る**）。
- **`review_integrated_*.md`** の削除または **git コミット**。
- **`r6-10-g`** の修復・削除。
- **original R6.13-B** / **stale R6.9-A** の削除・merge。
- **stale** `work/r6-9-a-veto-display-common` / **`5c45103`** の **merge**。

## 3. Candidate discovery 結果

`git worktree list` および `find …/invest-alpha-os-r6-12-*` で次を確認（**remove 前**）:

| path | branch | clean | ancestor of `main` |
|---|---|---|---|
| …-r6-12-a 〜 …-r6-12-g | 各 `work/r6-12-*` | YES | YES |
| …-r6-12-veto-hotfix | `work/r6-12-veto-fomo-centralization-hotfix` | YES | YES |

**選定優先**: 依頼の **docs-only / test-only 優先**に照らし、**R6.12-F は docs-only の design フェーズ**（[docs/40_r6_12_f_us_report_opt_in_hardening_design.md](./40_r6_12_f_us_report_opt_in_hardening_design.md)）であり、 **`worktree` path とブランチ名の対応も明確**なため **`…-r6-12-f`** を **TARGET** とした。**`r6-10-g` は対象外**（依頼・絶対禁止）。

## 4. 選定 TARGET（absolute path）

- **`/Users/uotani/Projects/invest-alpha-os-r6-12-f`**
- **branch**: `work/r6-12-f-us-report-opt-in-hardening-design`
- **HEAD**: `2b2c1f7`

## 5. Preflight 結果

| チェック | 結果 |
|---|---|
| TARGET が **`invest-alpha-os-r6-12-*` 配下（R6.12 系）** | OK |
| `main` worktree でない | OK |
| **`r6-14-f` worktree でない** | OK |
| ディレクトリ存在（remove 前） | OK |
| `git worktree list` に登録あり | OK |
| `git status --short` | **clean**（空） |
| `git merge-base --is-ancestor`（branch → `main`） | **真** |
| `git branch --contains` | **`main` を含む** |

## 6. 実行コマンド（実施済み・1 回のみ）

```bash
cd /Users/uotani/Projects/invest-alpha-os
git worktree remove /Users/uotani/Projects/invest-alpha-os-r6-12-f
```

- **`rm -rf` は使用していない**。

## 7. 削除後確認

- **`test ! -d /Users/uotani/Projects/invest-alpha-os-r6-12-f`** → **ディレクトリ不在**。
- **`git worktree list`** に当該 path **なし**。

## 8. No-op は実施しない

本タスクでは **preflight がすべて合格**していたため **`git worktree remove` を実施**。no-op ではない。

## 9. 削除しなかったもの

- **branch 削除なし**（`git branch -d` / `git push --delete` **未実施**）。
- **remote branch 削除なし**。
- **stale R6.9-A** の worktree／branch **未処理**。
- **`r6-10-g`** **未処理**。
- **`review_integrated_20260515.md`** **未処理**（**コミットも削除もなし**）。
- **original R6.13-B** branch **未処理**。
- **他の `invest-alpha-os-r6-12-*` worktree**（**実行は 1 本のみに限定**）。

## 10. 次候補

- **R6.14-G**: next single cleanup or **r6-10-g** decision（**別承認** · **1 本ずつ**）。
