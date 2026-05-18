# R6.15-B — Safety gate automation (local PR gate)

**ステータス**: **ブランチ作業のみ**（**`main` 未反映**）。ブランチ: **`work/r6-15-b-safety-gate-automation`**。**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-15-b`。

---

## 1. 目的

- **Branch protection**（**main への direct push 禁止・PR 必須**）に合わせ、**PR 前のローカル安全ゲート**を自動化する。
- **`make main-gate`** → **`scripts/main_gate.sh`** で pytest / agent-final-check / diff チェック / secret・live HTTP パターン検査を一括実行。
- **`.pre-commit-config.yaml`** でコミット前の軽量チェック（禁止パス・secret パターン・live HTTP 許可フラグの誤コミット禁止）。

## 2. 非目的

- **`main` への direct push** や **PR なし merge**。
- **GitHub Actions workflow（`.github/workflows/*`）の変更**（Branch protection 本体は **GitHub UI** で設定）。
- **`merge-to-main` ターゲットの採用**（本リポジトリでは **`main-gate` のみ**）。
- **live HTTP 追加** · **production cache write** · **signals / Veto ロジック変更** · **US opt-in default 変更** · **worktree cleanup**。

## 3. `make main-gate` / `scripts/main_gate.sh`

| ステップ | 内容 |
|---|---|
| ブランチ | **`main` 上では実行不可**（feature branch のみ） |
| 同期 | **`origin/main` が HEAD の祖先**であること |
| テスト | **`pytest -q`** · **`make -s agent-final-check`** |
| diff | **`git diff --check origin/main...HEAD`** |
| secret | diff 内の典型 secret パターン拒否 |
| network/cache | diff 内の **live HTTP 許可**・**手動 cache write 実行フラグ** パターンを拒否 |
| 警告 | **`.github/` / `Makefile` / `pyproject.toml`** 変更時は PR で明示レビュー促し |

## 4. `.pre-commit-config.yaml`

- **pre-commit-hooks**（空白・EOF・merge conflict・大ファイル・yaml/toml）。
- **local hooks**：禁止パス（`.env` 等）· staged secret パターン · live HTTP 許可 env の誤コミット禁止。

導入例（任意・ローカル）: `pip install pre-commit && pre-commit install`

## 5. Branch protection（運用メモ）

- **GitHub リポジトリ設定**で **main** に **PR 必須**・**required checks（`tests`）** を有効化する（**本タスクは UI 操作を含まない**）。

## 6. 次候補

- **R6.15-C**: US cache population runbook（別承認）。
- **R6.14-J**: cleanup continuation（別承認）。
