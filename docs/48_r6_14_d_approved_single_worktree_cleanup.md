# R6.14-D — Approved single worktree cleanup

**ステータス**: 作業ブランチ `work/r6-14-d-approved-single-worktree-cleanup` のみ（**`main` 未反映**）。**本記録は承認済み 1 worktree の `git worktree remove` のみ** — **`rm -rf`・local/remote branch 削除・他 path の削除は行っていない**。

---

## 1. 目的

- 依頼で **明示承認された 1 本**の worktree を **`git worktree remove` のみ**で解除し、ローカル作業場の整理を **安全に 1 歩**進める。

## 2. 非目的

- **`/Users/uotani/Projects/invest-alpha-os-r6-13-c` 以外**の worktree 削除。
- **local / remote branch 削除**（`work/r6-13-c-project-cleanup-readiness` ブランチは **残存し得る**）。
- **`review_integrated_*.md`** の削除または **git コミット**。
- **`r6-10-g`** の修復・削除。
- **original** `work/r6-13-b-us-report-opt-in-operational-readiness` の削除。
- **stale** `work/r6-9-a-veto-display-common` / **`5c45103`** の **merge** または削除。

## 3. ユーザー承認済み対象（absolute path）

- **`/Users/uotani/Projects/invest-alpha-os-r6-13-c`**
- **理由（要約）**: R6.13-C **project cleanup readiness** 用 worktree · 内容は **`main` に `d034d16` として統合済み**（docs-only）· 参照優先度が低い。

## 4. Preflight 結果

| チェック | 結果 |
|---|---|
| path が承認値と一致 | OK |
| `main` worktree ではない | OK |
| 本作業 `r6-14-d` worktree ではない | OK |
| ディレクトリ存在（remove 前） | OK |
| `git worktree list` に登録あり | OK |
| `git status --short` | **clean**（空） |
| branch | `work/r6-13-c-project-cleanup-readiness` |
| HEAD | `d034d16` |
| `git merge-base --is-ancestor`（`work/r6-13-c-project-cleanup-readiness` → `main`） | **真** |
| `git branch --contains work/r6-13-c-project-cleanup-readiness` | **`main` を含む** |

## 5. 実行コマンド（実施済み・1 回のみ）

```bash
cd /Users/uotani/Projects/invest-alpha-os
git worktree remove /Users/uotani/Projects/invest-alpha-os-r6-13-c
```

- **`rm -rf` は使用していない**。

## 6. 削除後確認

- **`test ! -d /Users/uotani/Projects/invest-alpha-os-r6-13-c`** → **ディレクトリ不在**。
- **`git worktree list`** に **`r6-13-c` の path が含まれない**ことを確認。

## 7. 削除しなかったもの

- **branch 削除なし**（`git branch -d` / `git push --delete` **未実施**）。
- **remote branch 削除なし**。
- **stale R6.9-A** の worktree／branch **未処理**。
- **`r6-10-g`** **未処理**（競合マーカーは **`main` とは別問題**のまま）。
- **`review_integrated_20260515.md`** **未処理**（**コミットも削除もなし**）。
- **original R6.13-B** branch **未処理**。

## 8. 次候補

- **R6.14-E**: 次の **単一 cleanup** または **branch cleanup proposal**（**別承認** · **1 本ずつ**）。
