# R6.14-A — Cleanup preflight inventory

**ステータス**: **完了・`main` 反映済み**（`cc33ef1` · branch CI **`25945410481`** · main merge push CI **`25945536823`**）。**本ドキュメントは棚卸し（inventory）のみ** — **`git worktree remove`・ディレクトリ削除・remote/local branch 削除は行わない**。

---

## 1. 目的

- ローカル **`invest-alpha-os-r6-*` worktree** と **`origin` 上の旧 topic branch** を **一覧化**し、後続フェーズで **誤削除・誤 merge** しないための **判断材料**を残す。
- **`main` の HEAD**（本 inventory 作成時点）を **正**とし、worktree 固有の汚染（例: 競合マーカー）と **混同しない**。

## 2. 非目的

- **削除実行**（worktree・branch・ファイル）。**R6.14-B でもユーザー明示承認なしに削除しない**方針。
- stale **`work/r6-9-a-veto-display-common` / `5c45103` の `main` merge**。
- **`docs/review_integrated_20260515.md`** および **`review_integrated_*.md`** の **git コミット**。

## 3. 現在の `main` HEAD（inventory 基準）

- **inventory 作成時点**: **`6d0989f`** — `docs: Record R6.13-C main completion`
- **`main` に本 inventory をマージ後**（参照用）: **`cc33ef1`** — `docs: R6.14-A cleanup preflight inventory`

## 4. stale branch inventory（参照のみ）

| 区分 | 例 | メモ |
|---|---|---|
| **merge 禁止（stale）** | `work/r6-9-a-veto-display-common`（`5c45103`） | 方針どおり **`main` へ merge しない**。 |
| **original（履歴参照）** | `work/r6-13-b-us-report-opt-in-operational-readiness`（`fa2741f`） | **`main` 未統合**。squash 経路で実装は `main` 済み。 |
| **squash 取り込み済** | `work/r6-13-b-us-report-opt-in-operational-readiness-squash` | **`main` に ff 統合済み**（`f42ccf6`）。 |
| **その他 `r6-10`〜`r6-13`** | 多数の `work/r6-*` | 多くは **過去タスク**。削除可否は **別判断**（本節では列挙のみ）。 |

## 5. `r6-10-g` conflict marker（`main` とは別問題）

- パス例: `/Users/uotani/Projects/invest-alpha-os-r6-10-g/docs/01_development_status.md`
- **`<<<<<<<` / `=======` / `>>>>>>>` が残留**（read-only 確認）。**`main` ツリーには含まれない**。

## 6. `review_integrated_*.md`（コミット禁止）

| パス | メモ |
|---|---|
| `invest-alpha-os/docs/review_integrated_20260515.md` | **untracked 想定** · **コミットしない**。 |
| `Downloads/review_integrated_20260515.md` | リポジトリ外コピー。**git 対象外**。 |

## 7. worktree candidates（`git worktree list` より抜粋）

| path | branch（概ね） | 分類案 |
|---|---|---|
| `/Users/uotani/Projects/invest-alpha-os` | `main` | **削除禁止** |
| `/Users/uotani/Projects/invest-alpha-os-r6-14-a` | `work/r6-14-a-cleanup-preflight-inventory` | **削除禁止**（本作業） |
| 各 `…-r6-9-*` / `…-r6-10-*` … `…-r6-13-*` | 各 `work/r6-*` | **要確認**（未 push 有無・参照価値） |
| `…-r6-13-b-squash` | squash branch | **削除候補**（`main` 済み・参照不要なら）※ **承認後のみ** |
| `…-r6-10-g` | `work/r6-10-g-…` | **要確認**（競合マーカー） |

> **分類ルール（案）**  
> - **削除禁止**: `main` worktree · **現在の R6.14-A worktree** · **未 `main` 反映 branch 専用 worktree**（誤認防止のため原則禁止側に寄せる）。  
> - **要確認**: original R6.13-B · stale R6.9-A · `r6-10-g` · `review_integrated` 類。  
> - **削除候補**: **`main` 反映済み**かつ **完了 docs 済み**の古い worktree · squash 統合のみが目的だった worktree 等 — **それでも R6.14-B で承認後のみ**。

## 8. branch candidates（`git branch -a` 抜粋・件数目安）

- `r6-9-a` / `r6-10` / `r6-11` / `r6-12` / `r6-13` / `r6-14` 系: **60 本前後**が `origin` またはローカルに残存（正確数は環境依存）。**本 inventory では削除・整理実行をしない**。

## 9. 削除実行前チェックリスト（R6.14-B 以降・承認必須）

1. **`git worktree list`** で **他 checkout がない**こと。  
2. **`git status` / `git log`** で **未 push がない**こと。  
3. **stale branch を `main` に merge しない**こと（特に **`5c45103`**）。  
4. **競合マーカー付きファイルを正本にしない**こと。  
5. **`review_integrated_*.md` を誤コミットしない**こと。

## 10. 次フェーズ — R6.14-B cleanup execution proposal

- **内容案**: R6.14-A の表を前提に、**削除候補ごとのコマンド案**と **承認ゲート**を **docs-only** で固定する（**実行しない**）。
- **制約**: **ユーザー明示承認なしに削除しない**。R6.14-C 以降の **実 `git worktree remove` は別承認**。
- **product / workflow / Makefile**: 変更しない。

## 11. 完了検証サマリ（`main` 反映後）

- **ブランチ**: `work/r6-14-a-cleanup-preflight-inventory`
- **実装コミット**: `cc33ef1`（docs-only）
- **CI**: branch tests **`25945410481`** · **main** merge 直後 tests **`25945536823`**
- **テスト**: full pytest **697 passed** · `make agent-final-check` success
- **方針**: **削除なし** · **`review_integrated` コミット禁止** · stale **`5c45103` merge 禁止** · 次 **R6.14-B**（コマンド案のみ）
