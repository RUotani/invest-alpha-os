# R6.14-H — Approved single R6.12 worktree cleanup and r6-10-g decision

**ステータス**: **完了・`main` 反映済み**。**`main` に取り込まれた tip**: `bf75781`。**作業ブランチ**: `work/r6-14-h-approved-single-worktree-cleanup-and-r6-10-g-decision`。単一の **`invest-alpha-os-r6-12-*` worktree** について `git worktree remove` を **1 回**実施（**`…-r6-12-e`**）。**`r6-10-g`** は **docs のみ**（削除・修復・merge なし）。**ブランチ CI**: **`25951001581`** success · **`main` push CI（`bf75781` の `main` merge）**: **`25951076732`** success。**検証**: full pytest **697 passed** · agent-final-check success（記録）。

---

## `main` 反映完了記録（本書の追記パート）

**完了記録 commit**: **`docs: Record R6.14-H main completion`**（追記後の `main` HEAD を参照。直後の `main` CI は `gh run list --branch main` で確認。）

---
## 1. 目的

1. `invest-alpha-os-r6-12-*` の残余について、優先順（**e → d → c → b → a → veto-hotfix**）で **preflight が最初に PASS した 1 path のみ**を `git worktree remove` する。**見つからなければ no-op**。今回は **`r6-12-e`** が PASS したため削除を実施した。
2. `r6-10-g` worktree が **競合マーカーを含む局所状態**にあることと、**`main` の健全性を混同しない**ことを docs で整理する。**本タスクでは `r6-10-g` の削除も修復 merge も行わない**。

## 2. 非目的

- main worktree と **`invest-alpha-os-r6-14-h`** の削除。
- **`invest-alpha-os-r6-10-g`** の削除・修復。**`rm -rf`**。許可されていない **`invest-alpha-os-r6-12-*` を 2 本目として削除しない**こと。
- **`review_integrated_*` の削除または git コミット**。**stale R6.9-A の main merge**。**original R6.13-B 削除**。**local / remote branch の明示削除**。

## 3. Candidate discovery と選定順

存在するものから **上へ優先順**：

1. `…/invest-alpha-os-r6-12-e`
2. `…/invest-alpha-os-r6-12-d`
3. `…/invest-alpha-os-r6-12-c`
4. `…/invest-alpha-os-r6-12-b`
5. `…/invest-alpha-os-r6-12-a`
6. `…/invest-alpha-os-r6-12-veto-hotfix`

**共通条件**: **`main` と `r6-14-h` 以外の path**、**名前付き branch**（detach 禁止）、**clean**、`merge-base --is-ancestor BRANCH main` が **真**。

## 4. TARGET（削除した absolute path）

- **`/Users/uotani/Projects/invest-alpha-os-r6-12-e`**
- **branch**: `work/r6-12-e-us-report-opt-in-cli`
- **削除直前 HEAD**: **`4b0aee8`**

## 5. Preflight 結果（本 TARGET）

| チェック | 結果 |
|---|---|
| `invest-alpha-os-r6-12-*` 配下 | OK |
| main / **`r6-14-h`** ではない | OK |
| **存在・`git worktree list` 登録** | OK |
| **`git status` clean** | OK |
| `merge-base --is-ancestor`（branch → `main`） | **真** |
| `branch --contains` に `main` | **あり** |

## 6. 実行コマンド（1 回のみ）

```bash
cd /Users/uotani/Projects/invest-alpha-os
git worktree remove /Users/uotani/Projects/invest-alpha-os-r6-12-e
```

## 7. 削除後確認

- 当該 path は **ディレクトリとしては存在しない**。
- **`git worktree list`** に当該 path **なし**。

## 8. No-op

- **当てはまらず**（本タスクでは **remove を実行**）。

## 9. **`r6-10-g` decision（docs／実行禁止のまとめ）**

- **`invest-alpha-os-r6-10-g`** は、**ワークツリー内部に競合マーカーなどのローカル汚染がある**状態とみなされ、**`main` が green であっても「main が壊れている」の意味とは別**。
- **修復のための大口 PR は不要という判断を基本**。実際の削除はユーザー承認付き・後続 **R6.14-I** 以降などの単一 **`git worktree remove`** で扱うとよい、という推奨。
- **本タスクの遵守結果**: **`r6-10-g` に対し delete／修復編集／merge／branch 削除／remote 削除 は一切しない**。

## 10. 削除しなかったもの

- **TARGET** 以外のすべての **`invest-alpha-os-r6-12-*` worktree**（許可は **1 本のみ**）。
- **`r6-10-g`**（前文の決定どおり）。
- **`review_integrated_20260515.md`**。stale **`work/r6-9-a-veto-display-common` / `5c45103`** の処理。明示的な **branch 削除**。

## 11. 次候補

- **R6.14-I**: ブランチ **`work/r6-14-i-approved-single-worktree-cleanup`** — **`invest-alpha-os-r6-12-*`** から safe な **1 本のみ**（優先 **`…/invest-alpha-os-r6-12-d`** の順で試行）。**残り R12 clean 系を終えた後の `r6-10-g`（承認付き）**は **後続で別判断**。**`main` に未マージ**。
