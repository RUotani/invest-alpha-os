# R6.13-C — Project cleanup readiness

**ステータス**: **完了・`main` 反映済み**（`d034d16` · branch CI **`25945163275`** · main merge push CI **`25945280440`**）。**本ドキュメントは方針の明文化のみ**（worktree の物理削除・branch の force 操作・stale の **merge は行わない**）。

---

## 1. 目的

- ローカルに蓄積した **`invest-alpha-os-r6-*` worktree** と **古い topic branch** を、**安全に整理する前**の **readiness（棚卸し・判断材料）** としてまとめる。
- **`main` は正常**であることと、**特定 worktree の破損（競合マーカー残留）** を混同しない。

## 2. 非目的

- **`git worktree remove`** やディレクトリの **`rm -rf`** による **実削除**（別途ユーザー承認のうえで実施）。
- stale branch の **`main` merge**（特に `work/r6-9-a-veto-display-common` / `5c45103` は **merge 禁止**のまま）。
- **`docs/review_integrated_20260515.md`** の **git コミット**（運用メモとしてローカルに残る場合は **`.gitignore` 対象外の untracked** として扱い、push しない）。
- product コード・Makefile・`.github/workflows` の変更。

## 3. `main` の健全性

- **`main`** は CI と pytest で緑を維持している前提で作業する（worktree のローカル汚染は **`main` の品質を意味しない**）。

## 4. stale branch（参照用・この節では merge しない）

| 例 | 備考 |
|---|---|
| `work/r6-9-a-veto-display-common`（`5c45103`） | **stale · `main` merge 禁止**（過去方針どおり）。 |
| `work/r6-9-a-veto-result-centralization-rebase` | rescue 系。必要なら別途履歴確認のうえ整理。 |
| `work/r6-10-g-us-cache-metrics-command-hardening` ほか `r6-10`〜`r6-12` の各 work branch | 多くは **過去タスク**。`origin` に残存しているものは **参照のみ**でよい。 |
| `work/r6-13-b-us-report-opt-in-operational-readiness` | **original** R6.13-B。**`main` へは squash branch のみ反映済み**（本ブランチは履歴用に残存し得る）。 |
| `work/r6-13-b-us-report-opt-in-operational-readiness-squash` | **clean** 取り込み元。`main` 反映後も worktree を即削除する必要はない。 |

## 5. 既知の worktree 異常（`main` とは切り離す）

- **`/Users/uotani/Projects/invest-alpha-os-r6-10-g`** の `docs/01_development_status.md` に **Git 競合マーカー**（`<<<<<<<` / `=======` / `>>>>>>>`）が **423 行付近に残留**（read-only 確認のみ。本リポジトリの `main` ツリーには含まれない）。

## 6. worktree 削除候補（例・削除はしない）

以下は **「不要になったら候補」** であり、**このドキュメントが削除を指示するものではない**。

- マージ済み・**追跡不要**と判断した `invest-alpha-os-r6-10-*` … `r6-12-*` の個別 worktree。
- R6.13-B **original** 用 `/Users/uotani/Projects/invest-alpha-os-r6-13-b`（squash 取り込み後、参照不要なら）。
- 重複検証用の `/Users/uotani/Projects/invest-alpha-os-r6-13-b-squash`（**任意**）。

**推奨順序**: read-only **`git worktree list`** 棚卸し → **ユーザー承認** → 対象ブランチが他で不要か確認 → **`git worktree remove <path>`**（手順は Git 公式／社内 runbook に従う）。

## 7. 削除前チェックリスト

1. 対象 worktree で **未 push のコミットがない**こと（`git status` / `git log origin/..HEAD`）。
2. 対象が **`main` の唯一のチェックアウト先でない**こと。
3. stale branch を **誤って `main` に merge しない**こと（特に **`5c45103`** 系）。
4. 競合マーカー付きファイルを **正本としてコミットしない**こと。

## 8. 次候補

- **R6.14-A**: cleanup **preflight inventory**（tables・分類案のみ。**削除なし**）。
- **R6.14-B**（案）: cleanup **実行**（ユーザー明示承認後のみ）・`review_integrated_*.md` 運用の正規化。

## 9. 完了検証サマリ

- **ブランチ**: `work/r6-13-c-project-cleanup-readiness`
- **実装コミット**: `d034d16`（docs-only）
- **CI**: branch tests **`25945163275`** · **main** merge 直後 tests **`25945280440`**
- **テスト**: full pytest **697 passed** · `make agent-final-check` success
- **方針**: stale **`5c45103` merge 禁止** · `r6-10-g` 競合は **main とは別問題** · **`review_integrated_20260515.md` はコミットしない**
