# R6.9 以降 — 並行開発の準備メモ（実装は未開始）

**ステータス**: 手順・境界のメモのみ（**R6.9 のコード変更は開始しない**）  
**前提**: `main` へは **ChatGPT 確認後**に取り込む方針とし、本メモは **作業前の合意形成用**。

---

## 1. この文書の位置づけ

- **目的**: 複数トピックを同時に進めないために混乱するポイント（ブランチ、`git worktree`（同一リポジトリから別作業ディレクトリを作る仕組み）、検証）を **1 か所に固定**する。
- **範囲外**: R6.9 の機能設計の確定、実装、本番向け設定変更、**live HTTP**、**production cache write**。

---

## 2. いま止めておくこと（依頼で禁止されているものの再掲）

次は **実施しない**（別途明示がない限り）。

- R6.9 の **実装開始**
- **複数 `git worktree`** を使った **実作業の並列化**（準備の読み物としての理解は可）
- `main` への **未レビュー・別機能の混入**
- **Pull Request** の作成（運用が変わるまで）
- **`.github/workflows/*`** および **`Makefile`** の変更
- **`safe-push`** スクリプトの変更
- **`ALLOW_IMPORTANT=true`** の利用
- **US 株スコープ**の拡大、**package rename**
- **`merge commit`** による取り込み（**fast-forward merge（早送り取り込み）** のみ）

---

## 3. 推奨ブランチ運用（単一 worktree の場合）

1. `main` を最新化: `git fetch origin main` → `git checkout main` → `git pull --ff-only origin main`
2. 作業ブランチ作成: `git checkout -b work/r6-9-<topic-slug>`（`<topic-slug>` は英小文字・ハイフンで内容が分かる短い名）
3. 作業・コミットは **当該ブランチのみ**。
4. `main` へ戻すときは **早送り取り込み可能なときだけ** `git merge --ff-only work/r6-9-...`。**コンフリクト**が出たら **無理に解消して `main` に載せない**（先に `main` 側か作業側を整理）。

---

## 4. `git worktree` を使う場合（準備レベル）

**実作業を複数ディレクトリで並列に始めない**ことを前提に、将来使うときのメモのみ。

- 追加 worktree は **`main` と作業ブランチを混同しないパス**に置く（例: リポジトリ外の兄弟ディレクトリ、または組織ルールに従った `../invest-alpha-os-r69` など）。
- 各 worktree で **`git status`** を必ず確認し、**同じブランチを二重チェックアウトしない**。
- 初回は **`git worktree add --help`** を読み、削除時は **`git worktree remove`** で掃除する。

---

## 5. 取り込み前チェックリスト（R6.9 用・再利用可）

- **`PYTHON=.venv/bin/python`（またはプロジェクト標準）** で **`pytest`** 全文
- **`make agent-final-check`**（プロジェクト標準の総合ゲート）
- **変更意図と無関係なファイルが混ざっていないか**（`git diff --stat`）
- **秘密情報**（`.env`、鍵、トークン）がコミットに含まれていないか
- **`config/veto_rules.yaml`** を触る場合は **過検知・表示文言** を `docs/16_r6_8_d_veto_volume_spike_design.md` など既存設計と照合

---

## 6. 関連ドキュメント

- 進捗の単一ソース: [docs/01_development_status.md](./01_development_status.md)
- AI 作業フロー: [docs/07_ai_development_workflow.md](./07_ai_development_workflow.md)
- 出来高急増ルールの設計経緯: [docs/16_r6_8_d_veto_volume_spike_design.md](./16_r6_8_d_veto_volume_spike_design.md)

---

**更新方針**: R6.9 のスコープが固まったら、本ファイルの **「1. この文書の位置づけ」** に **実装開始済み** の日付と **ブランチ名** を追記し、`01_development_status.md` に **R6.9 節**を追加する。
