# AI 開発運用ルール（Phase 0 完了後）

Laputa Alpha OS / InvisAlphaOS で、複数 AI / ツールと人間が協働するときの**役割分担・許可コマンド・標準フロー**を定義する。この文書は「開発効率」と「セキュリティ・責務分離」を両立させるための運用規約であり、コードの代替ではない。

## 1. Cursor Agent の役割

- **実装担当**：リポジトリ内のコード・設定・ドキュメント追加・修正の主担当。
- **検証**：変更後、`PYTHON=.venv/bin/python make verify` まで実行し、テスト・基本 CLI 動作を確認する。
- **禁止**：**`git add` / `git commit` / `git push` は実行しない**。コミットとプッシュは人間のみが実行し、AI は明示依頼があっても実行しない。

## 2. Codex の役割（レビュー担当）

コードの主実装は行わず、レビューと調査に集中する。

- **差分レビュー**：変更内容が目的・設計ドキュメントと整合するか確認する。
- **CI 失敗の調査**：GitHub Actions ログとローカル再現を照らし、原因を切り分ける。
- **セキュリティ・責務分離レビュー**：機密の混入、自動売買の誤導線、Observation Only の逸脱がないかを確認する。

## 3. Claude Code の役割（仕様レビュー・大きめ改善担当）

- **仕様レビュー**：機能要件・フェーズ境界・運用時間・リスク方針と矛盾がないかを見る。
- **大きめの改善案**：アーキテクチャ単位や複数ファイルにまたがる提案を整理する。
- **別ブランチでの実装候補**：大きな変更は「別ブランチで試す」と明示し、本体への取り込みはレビュー後とする。

## 4. AI に許可するコマンド（例）

許可リストは運用単位で拡張してよい。初期の目安：

- `PYTHON=.venv/bin/python make verify`（または `make verify` — Makefile が `.venv/bin/python` を優先する場合あり）
- `make codex-review` / `make ai-check`（**`git add` / `commit` は行わない**。レビュー結果は `.ai/reviews/*.md` でローカルのみ）
- `git status --short`
- `git diff --stat`
- `pytest`（またはプロジェクト標準に従ったテスト実行）
- 調査対象が明確な範囲での `cat`（または Read ツールでのファイル読込）

読み取り専用の探索（`grep` / `find` など）はタスクに応じて許可できる。機密ファイルや `outputs/` の実行生成物は**リポジトリにコミットしない**こと（詳細は下記「Git に載せないもの」）。

## 5. AI に禁止するコマンド

以下は**デフォルトで禁止**する。

- `git add`
- `git commit`
- `git push`
- `rm` / `rm -rf`
- `.env` の作成・編集・コピー・転載・コミット
- `credentials.json` / `token.json` の作成・編集・コピー・転載・コミット
- `secrets/`、`credentials/` 配下ファイルの同上
- `curl | bash`
- `brew install`
- （その他）外部 API を実キーで叩く操作

## 6. 標準作業フロー

1. **Cursor** が実装（必要に応じてドキュメント・テストも同時）。
2. ローカルで **`PYTHON=.venv/bin/python make verify`**（または CI と揃える `PYTHON=python make verify`）を実行。
3. **Codex** が差分・セキュリティ・CI をレビュー。
4. **承認ゲート**：**`git add` / `git commit` / `git push` は人間のレビューと明示承認のうえでのみ実行**する。AI は実行しない。
5. **GitHub Actions** がグリーンか確認する。

Observation Only・No Auto Trading、`outputs/` 実行生成物の Git 非管理など、プロジェクト規約は常に適用する。

### 6.1 Codex レビューの半自動化（CLI）

手動コピペを減らすため、`codex exec` でレビューを走らせ、結果だけを Markdown ファイルに保存するターゲットを用意している。

- **`make codex-review`**  
  - `codex` が PATH に無い場合は **エラー終了とはせず**、説明付きで `.ai/reviews/latest.md` にスキップ理由を書き、`make` は続行できる（終了コード 0）。
  - ある場合は **`codex exec` を read-only サンドボックス、`--ask-for-approval never`、`--ephemeral` で実行**（標準どおりモデル実行は OpenAI 側との通信となる）。`.env` は **読み込まず**、`git status --short` と `git diff --stat` だけをプロンプトコンテキストに含める。
  - 結果は **`.ai/reviews/latest.md`**（**Git 管理外**: `.gitignore` で `.ai/reviews/*.md` を無視）。
- **`make ai-check`**  
  - **`PYTHON=...` をサブ Makefile に明示渡し**したうえで **`make verify`** → **`make codex-review`** → **`git status --short`** の順。

レビュー観点（スクリプト内プロンプトの要約）: Phase 範囲、機密・outputs 混入、Actions 耐性、`make verify` 構造、意図しない API 実接続、トークン／raw のログ出力、config / docs / src の責務分離。**リポジトリの書き換えや `git add` / commit / push はレビューターゲットが行わないこと**を前提とする。

## Git に載せないもの（人間・AI 共通）

リポジトリに入れず、レビューやログへの転載も避ける運用とする。

- `.env`、`credentials.json`、`token.json`、`secrets/`、機密となるキー一式
- `outputs/` に生成される実行結果・実運用ログ（実データ）。`.gitignore` と README に従い、ディレクトリ維持用の `.gitkeep` のみ管理等

## 7. Phase 1a 以降のタスク分割ルール

- **1 タスク = 1 目的 + 1 実装 + 1 テスト（または検証テスト追加）+ 1 verify** が目安。
- **API の実接続**は本体に入れる前に、**stub とテスト**でインタフェース・失敗モード・機密フローを固める。
- **outputs に落ちる実データ**は**原則 Git 管理外**（Phase 0 完了報告および `.gitignore` 方針に従う）。

---

関連：[01_development_status.md](./01_development_status.md) · [06_phase0_completion_report.md](./06_phase0_completion_report.md)
