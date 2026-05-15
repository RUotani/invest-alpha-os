# R6.14-B — Cleanup execution proposal

**ステータス**: 作業ブランチ `work/r6-14-b-cleanup-execution-proposal` のみ（**`main` 未反映**）。**本ドキュメントは「削除コマンド案」と承認ゲートの明文化のみ** — **ここに書かれたコマンドを自動実行しない** · **`git worktree remove` / `rm` / `git branch -d` / `git push --delete` は行わない**。

**`main` 基準 HEAD（本 proposal 作成時点）**: **`94b20bb`** — `docs: Record R6.14-A main completion`

---

## 10.1 目的

- **[docs/45_r6_14_a_cleanup_preflight_inventory.md](./45_r6_14_a_cleanup_preflight_inventory.md)** の inventory を前提に、**削除実行前の最終提案**（候補・順序・コマンド雛形・承認ゲート）を固定する。
- **実削除はしない**。ユーザー明示承認後の **R6.14-C 以降**で初めて実行を検討する。

## 10.2 非目的

- **worktree 削除** · **local / remote branch 削除** · **`review_integrated_*.md` の削除または git コミット**。
- stale branch の **`main` merge**（特に **`work/r6-9-a-veto-display-common` / `5c45103`**）。
- **product コード**・**Makefile**・**`.github/workflows`** の変更。

## 10.3 Candidate 分類（R6.14-A 整合）

### A. 削除実行候補（ユーザー承認後のみ検討）

**すべての条件を満たす場合に「候補」**であり、**本節では実行しない**。

- `main` 反映済み · 関連 **完了 docs 済み** · 当該 topic の **CI success 履歴あり**。
- **現在作業中の worktree でない**（`git worktree list` で確認）。
- **参照価値が低い**とオペが判断した場合のみ。

**例（コマンドは実行しない）**:

| 候補 path（例） | 根拠メモ |
|---|---|
| `/Users/uotani/Projects/invest-alpha-os-r6-13-b-squash` | R6.13-B **squash 統合済み**（`f42ccf6` が `main`）。一時検証用。 |
| `/Users/uotani/Projects/invest-alpha-os-r6-13-c` | R6.13-C **docs は `main` 済み**（`d034d16`）。 |
| 古い `…-r6-12-*` worktree（個別判断） | 多くは **過去タスク**。**未 push / ローカル独自変更がないか**を必ず確認。 |

### B. 要確認・保留（原則ここから外さない）

| 対象 | メモ |
|---|---|
| **`work/r6-13-b-us-report-opt-in-operational-readiness`**（original） | **`main` 未統合**履歴。削除・remote 削除は **別判断**。 |
| **`work/r6-9-a-veto-display-common` / `5c45103`** | **stale · `main` merge 禁止**。 |
| **`/Users/uotani/Projects/invest-alpha-os-r6-10-g`** | `docs/01_development_status.md` に **競合マーカー残留**。**`main` ツリーとは無関係**。修復 or worktree remove は **別承認**。 |
| **`review_integrated_*.md`**（例: repo 直下 `docs/review_integrated_20260515.md` · `Downloads/` コピー） | **git コミット禁止**。**削除も本 proposal 範囲外**（運用で扱う）。 |

### C. 削除禁止

| 対象 | メモ |
|---|---|
| **`/Users/uotani/Projects/invest-alpha-os`（`main`）** | 正本。 |
| **`/Users/uotani/Projects/invest-alpha-os-r6-14-b`（本作業）** | 現在の R6.14-B worktree。 |
| **未 `main` 反映 branch 専用 worktree** | 誤削除防止のため **原則禁止側**。 |

## 10.4 実行コマンド案（DRY-RUN / 記載のみ）

**以下は実行しない。** ユーザー承認後に **1 件ずつ**コピーして使う前提の **雛形**。

```bash
# DRY-RUN ONLY — do not run without user approval
git worktree list
git status
git -C /Users/uotani/Projects/invest-alpha-os branch --show-current

# After explicit user approval only (examples):
# git worktree remove /Users/uotani/Projects/invest-alpha-os-r6-13-b-squash
# git branch -d work/r6-13-b-us-report-opt-in-operational-readiness-squash
# git push origin --delete work/some-old-topic-branch
```

## 10.5 承認ゲート（R6.14-C で削除に進む前に必須）

ユーザーから **書面またはチャットで明示**された項目が揃うまで **削除しない**。

1. **削除対象 worktree の絶対パス**（複数なら列挙）。  
2. **削除対象 local branch**（あれば）· **remote branch 名**（`--delete` する場合）。  
3. **削除しない branch / worktree** のリスト。  
4. **バックアップ不要**であること（またはバックアップ取得済み）。  
5. **`main` が最新かつ clean**（`git status` / `git pull --ff-only` 済み）。  
6. **stale `5c45103` を `main` に merge しない**ことの再確認。

## 10.6 次候補

- **R6.14-C**: **approved cleanup execution**（上記ゲートを満たした場合のみ · **承認なし実行禁止**）。
