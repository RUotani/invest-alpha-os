# R6.14-G — Approved single old R6.12 worktree cleanup

**ステータス**: **完了・`main` 反映済み**。**作業ブランチ**: `work/r6-14-g-approved-single-worktree-cleanup`。単一の `invest-alpha-os-r6-12-*` worktree に対する `git worktree remove`（**1 回のみ**）。**検証**: full pytest **697 passed**・agent-final-check success（記録のみ）。**ブランチ CI**: **`25950768633`** success · **`main` push CI**（`488abfe` 取り込み）: **`25950906910`** success。

---

## `main` 反映完了記録（本ファイルの記録段落）

**完了記録 commit**: **`docs: Record R6.14-G main completion`**（追記後 `main` HEAD を参照。その直後 `main` CI は `gh run list --branch main` で確認。）

---

## 1. 目的

- 古い **R6.12** 系 **`invest-alpha-os-r6-12-*`** のうち **承認どおり** `/Users/uotani/Projects/invest-alpha-os-r6-12-g` を優先候補として評価する。`main` に **ancestor で含まれ**、かつ **clean** であれば、当該 **1 本**に限り `git worktree remove` する（**`r6-14-g` 作業 worktree 削除は禁止**。**不合格なら no-op** — 今回は **合格のため remove 実施**）。

## 2. 非目的

- **`invest-alpha-os-r6-14-g`** や **`invest-alpha-os`**（**main worktree**）の削除・変更。
- **`r6-10-g`**（競合／修復）。
- **`/Users/uotani/Projects/invest-alpha-os-r6-12-g` 以外を同じタスク内で複数削除**。
- **`review_integrated_*`** の削除またはコミット。
- **original R6.13-B**／**stale R6.9-A**／**merge**。**local / remote branch 削除単体**。
- **`rm -rf`**。

## 3. Candidate discovery 結果

`git worktree list` と `find … -name 'invest-alpha-os-r6-12-*'`（**実施環境依存**）において、`r6-12-f` は **過去タスクですでに remove** 済み。その他、`r6-12-a` 〜 **`g`** と **`…-veto-hotfix`** 等がリストにあったが、承認済み選択規則に従い **優先候補** `/Users/uotani/Projects/invest-alpha-os-r6-12-g` を評価：**存在**・**named branch** で **clean**・**ancestor of `main`** → **preflight PASS** と判断し **それ以外の削除は行わない**。

## 4. 選定 TARGET（absolute path）

- **`/Users/uotani/Projects/invest-alpha-os-r6-12-g`**
- **branch**: `work/r6-12-g-us-report-opt-in-hardening`
- **HEAD**: `52d3d49`

## 5. Preflight 結果

| チェック | 結果 |
|---|---|
| **`invest-alpha-os-r6-12-*` 配下** | OK |
| `main` / **`r6-14-g`** worktree と別 | OK |
| ディレクトリ存在・`worktree list` 登録 | OK |
| `git status --short` | **clean**（空） |
| `merge-base --is-ancestor` branch → **`main`** | **真** |
| `branch --contains` に **`main`** | **あり** |

## 6. 実行コマンド（実施済み・1 回のみ）

```bash
cd /Users/uotani/Projects/invest-alpha-os
git worktree remove /Users/uotani/Projects/invest-alpha-os-r6-12-g
```

## 7. 削除後確認

- **`test ! -d /Users/uotani/Projects/invest-alpha-os-r6-12-g`** → **ディレクトリ不在**。
- **`git worktree list`** に当該 path **なし**。

## 8. No-op

- **適用しない**（本タスクは **削除を実行**）。

## 9. 削除しなかったもの

- **その他すべての `invest-alpha-os-r6-12-*` worktree**（本タスクでは **2 本目以降は削除しない**。）
- **`r6-10-g`**、**review_integrated_*、stale/originalブランチ、remote/local branch削除**。**`rm -rf`**。

## 10. 次候補

- **R6.14-H**: **`work/r6-14-h-approved-single-worktree-cleanup-and-r6-10-g-decision`** — 古い **`invest-alpha-os-r6-12-*`** から **safe な 1 本** と **`r6-10-g` の方針を docs で整理**。**優先** **`/Users/uotani/Projects/invest-alpha-os-r6-12-e`**。**`main` に未マージ**。
