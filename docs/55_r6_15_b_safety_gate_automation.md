# R6.15-B — Safety gate automation (local PR gate)

**ステータス**: **完了・`main` 反映済み**（PR **#2** · `e6e10c5`）。本書は運用メモ。

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
| ブランチ | **名前付き feature branch のみ**（**`main` 拒否** · **detached HEAD 拒否**） |
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

- **GitHub ruleset `main`**: **PR 必須** · required status check context **`test`**（workflow 名は `tests` だが check-run 名は job 名 `test`）。

## 6. 次候補

- **R6.15-C**: US cache population runbook（別承認）。
- **R6.14-J**: cleanup continuation（別承認）。
