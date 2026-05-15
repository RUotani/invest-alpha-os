# R6.14-C — Approved single worktree cleanup

**ステータス**: **完了・`main` 反映済み**（`b5a6e0f` · branch CI **`25945920148`** · main merge push CI **`25946097150`**）。**本記録の実行は承認済み 1 worktree の `git worktree remove` のみ** — **`rm -rf`・local/remote branch 削除・他 path の削除は行っていない**。

**作業ブランチ**（`main` へ fast-forward merge）: `work/r6-14-c-approved-single-worktree-cleanup`

**検証（merge 直前・`main`）**: full pytest **697 passed** · agent-final-check success（`review_integrated_20260515.md` は **未コミットのまま**）。

---

## 1. 目的

- 依頼で **明示承認された 1 本**の worktree を **`git worktree remove` のみ**で解除し、ローカル作業場の整理を **安全に 1 歩**進める。

## 2. 非目的

- **`/Users/uotani/Projects/invest-alpha-os-r6-13-b-squash` 以外**の worktree 削除。
- **local / remote branch 削除**（`work/r6-13-b-us-report-opt-in-operational-readiness-squash` ブランチは **残存し得る**）。
- **`review_integrated_*.md`** の削除または **git コミット**。
- **`r6-10-g`** の修復・削除。
- **original** `work/r6-13-b-us-report-opt-in-operational-readiness` の削除。
- **stale** `work/r6-9-a-veto-display-common` / **`5c45103`** の **merge** または削除。

## 3. ユーザー承認済み対象（absolute path）

- **`/Users/uotani/Projects/invest-alpha-os-r6-13-b-squash`**
- **理由（要約）**: R6.13-B **squash 統合用の一時 worktree** · 内容は **`main` に `f42ccf6` として統合済み** · 参照優先度が低い。

## 4. Preflight 結果

| チェック | 結果 |
|---|---|
| path が承認値と一致 | OK |
| `main` worktree ではない | OK |
| 本作業 `r6-14-c` worktree ではない | OK |
| ディレクトリ存在 | OK |
| `git worktree list` に登録あり | OK |
| `git status --short` | **clean**（空） |
| branch | `work/r6-13-b-us-report-opt-in-operational-readiness-squash` |
| HEAD | `f42ccf6` |
| `git merge-base --is-ancestor`（squash branch → `main`） | **真**（`SQUASH_ANCESTOR_OF_MAIN`） |
| `git branch --contains work/r6-13-b-us-report-opt-in-operational-readiness-squash` | **`main` を含む** |

## 5. 実行コマンド（実施済み・1 回のみ）

```bash
cd /Users/uotani/Projects/invest-alpha-os
git worktree remove /Users/uotani/Projects/invest-alpha-os-r6-13-b-squash
```

- **`rm -rf` は使用していない**。

## 6. 削除後確認

- **`test ! -d /Users/uotani/Projects/invest-alpha-os-r6-13-b-squash`** → **ディレクトリ不在**（`DIR_REMOVED_OK`）。
- **`git worktree list`** に **`r6-13-b-squash` の path が含まれない**ことを確認。

## 7. 削除しなかったもの

- **branch 削除なし**（`git branch -d` / `git push --delete` **未実施**）。
- **remote branch 削除なし**。
- **stale R6.9-A** の worktree／branch **未処理**。
- **`r6-10-g`** **未処理**（競合マーカーは **`main` とは別問題**のまま）。
- **`review_integrated_20260515.md`** **未処理**（**コミットも削除もなし**）。

## 8. 次候補

- **R6.14-D**: **承認済み単一 cleanup** — 対象 path **`/Users/uotani/Projects/invest-alpha-os-r6-13-c`**（**別ブランチ** · **`main` 未反映** · **1 本ずつ**）。

## 9. `main` 反映完了記録

- **`main` HEAD（R6.14-C 取り込み）**: `b5a6e0f` — `docs: R6.14-C approved single worktree cleanup`
- **branch CI**: **`25945920148`** success
- **main push CI（上記コミットの `main` push）**: **`25946097150`** success
- **本節および `docs/01_development_status.md` の完了表記**: コミット **`docs: Record R6.14-C main completion`** で記録（その push 直後の `main` CI は `gh run list --branch main` で確認）
