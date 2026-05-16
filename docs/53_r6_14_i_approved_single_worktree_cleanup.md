# R6.14-I — Approved single old R6.12 worktree cleanup

**ステータス**: **完了・`main` 反映済み**。**`main` に取り込まれた tip**: `304b822`。**作業ブランチ**: `work/r6-14-i-approved-single-worktree-cleanup`。単一の **`invest-alpha-os-r6-12-*` worktree** に対して `git worktree remove` を **1 回**実施（**`/Users/uotani/Projects/invest-alpha-os-r6-12-d`**）。**ブランチ CI**: **`25951158250`** success。**`main` push CI（`304b822` が `main` に反映）**: **`25951287619`** success。**検証**: full pytest **697 passed** · agent-final-check success（記録）。**`git worktree remove --force`**・**`rm -rf`** および **branch の明示削除**は **未実施**。

---

## `main` 反映完了記録（本書の追記パート）

**完了記録 commit**: **`docs: Record R6.14-I main completion`**（その直後の `main` tip と CI は `gh run list --branch main` で確認。**本段落追記より前の merge tip は **`304b822`**。）

---

## 1. 目的

- **`invest-alpha-os-r6-12-*`** の残余から、優先順（**d → c → b → a → veto-hotfix**）で **preflight が最初に PASS した 1 path のみ**を `git worktree remove` する。**見つからなければ no-op**。今回は **`r6-12-d`** が PASS したため削除を実施した。
- **`r6-10-g`** は **削除・修復・merge を行わず**、`main` と切り離した **「R12 clean 系完了後に別途承認」**方針のまま据え置く（本タスクは **docs に触れのみ**）。

## 2. 非目的

- **`invest-alpha-os`**（**main worktree**）や **`invest-alpha-os-r6-14-i`** の削除。**許可されていない複数削除**。
- **`invest-alpha-os-r6-10-g`** の削除・修復。**`rm -rf`**。許可のない **`invest-alpha-os-r6-12-*` の 2 本目削除**。**`review_integrated_*` の削除またはコミット**。**stale R6.9-A の merge**。**original R6.13-B 削除**。明示的な **local / remote branch** 削除単体。**`git worktree remove --force`**。

## 3. Candidate discovery と選定順

優先順（依頼どおり）：**`/Users/uotani/Projects/invest-alpha-os-r6-12-d`** → **`-c`** → **`-b`** → **`-a`** → **`-veto-hotfix`**。

**結果**: **`r6-12-d`** 〜 **`veto-hotfix`** は複数 **`git worktree list`** にあったが、`d` が **named branch・clean・`main` の ancestor** と確認できたため **単一許可どおりこの 1 本のみ**削除。他順位は評価前に試行終了した。

## 4. TARGET（削除した absolute path）

- **`/Users/uotani/Projects/invest-alpha-os-r6-12-d`**
- **branch**: `work/r6-12-d-us-report-opt-in-design`
- **削除直前 HEAD**: **`1e4013c`**

## 5. Preflight 結果（本 TARGET）

| チェック | 結果 |
|---|---|
| **`invest-alpha-os-r6-12-*`** 対象である | OK |
| **`invest-alpha-os`** / **`invest-alpha-os-r6-14-i` ではない** | OK |
| **存在・`git worktree list` 登録** | OK |
| **`git status --short`** | **clean**（空） |
| **`merge-base --is-ancestor`（branch → `main`）** | **真** |
| **`git branch --contains` に `main`** | **あり** |

## 6. 実行コマンド（1 回のみ）

```bash
cd /Users/uotani/Projects/invest-alpha-os
git worktree remove /Users/uotani/Projects/invest-alpha-os-r6-12-d
```

## 7. 削除後確認

- **`test ! -d /Users/uotani/Projects/invest-alpha-os-r6-12-d`** → **ディレクトリ不在**。
- **`git worktree list`** に当該 path **なし**。

## 8. No-op

- **当てはまらず**（本タスクでは **remove を実行**）。

## 9. **`r6-10-g`（未操作のまま）**

- **`invest-alpha-os-r6-10-g`** は **本タスクでは削除・修復・merge しない**（**R6.14-H** の decision を踏襲）。

## 10. 削除しなかったもの

- **TARGET 以外**の **`invest-alpha-os-r6-12-*` worktree**（**2 本目以降は削除禁止**）。
- **branch の明示削除・remote の明示削除**。**stale R6.9-A**。**original R6.13-B**。**`review_integrated_*`**。**`rm -rf`**。**`git worktree remove --force`**。

## 11. 次候補

- **R6.15-A**: **`work/r6-15-a-daily-header-and-stale-output-fix`** — daily report 冒頭文言の是正と **future stale output** の整理（**ブランチ作業のみ**）。**単一 R12 cleanup の継続**は **R6.14-J**。
