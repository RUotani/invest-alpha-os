# AI 開発運用ルール（Phase 0 完了後）

Laputa Alpha OS / InvisAlphaOS で、複数 AI / ツールと人間が協働するときの**役割分担・許可コマンド・標準フロー**を定義する。この文書は「開発効率」と「セキュリティ・責務分離」を両立させるための運用規約であり、コードの代替ではない。

## 1. Cursor Agent の役割

- **実装担当**：リポジトリ内のコード・設定・ドキュメント追加・修正の主担当。
- **検証**：変更後、`PYTHON=.venv/bin/python make verify` または `PYTHON=.venv/bin/python make ai-check` まで実行し、テスト・基本 CLI・Codex を確認する。
- **コミット / プッシュ**：**単体の raw `git add` / `git commit` / `git push` は禁止**（原則この経路以外にコミット／プッシュしない）。必要なときは **`SAFE_PUSH_MSG="..." PYTHON=.venv/bin/python make safe-push`**（ゲート済みパス）**のみ**。**`Makefile` はコミットメッセージをレシピ内で展開せず**、**`SAFE_PUSH_MSG` を環境として `scripts/safe_commit_push.sh` が検証したうえで `git commit -m` に渡す**。**門番には `scripts/safe_commit_push.sh` による三段階の禁止パス検査（詳細後述）・`make ai-check`・`.ai/reviews/latest.json` の機械読み取り（Markdown 本文ではない）**がある。

### 1.1 Safe Push Automation（運用規約）

- **目的**：人間が毎回変更ファイル一覧をチャットへ貼る手間を減らし、**安全検査に通ったときだけ**（AI または人間が）`commit` / `push` できるようにする。
- **AI は `make safe-push`（または同等のゲート済み自動化）以外で `git commit` / `push` してはならない**。
- **人間**は実行後 **[GitHub Actions](https://docs.github.com/en/actions) が green** かを確認する（ローカルの `safe-push` と役割分担）。
- **禁止パス（事前・事後・ステージの三段階）**：`safe-push` は **`make ai-check` より前に** `git status --short --untracked-files=all` 上のパスを検査する。**`.env`（`.env.example` 除く）、`credentials.json`、`token.json`、`secrets/`、`credentials/`、`keys/`、`outputs/` 実ファイル（`.gitkeep` のみ許可）、`.venv/` または `venv`、`.ai/reviews/` 直下の `.md`/`.json`、`.pem`/`.key` ファイル** が現れたら **即停止し、`verify` / Codex レビューも開始しない**。`ai-check` 成功後にも **同一基準で再検査**する。**ステージング**は **クリーンな index（事前に何も stage していないこと）を前提**とし、**リポジトリ全体の一括 `git add` は行わず**、**同じ `git status --short` 由来の候補パスのみ** `git add -- <paths>` で取り込み、その **直後もステージ内容のみ**を再検査する。**未解決のマージ競合（例: XY が `UU` / `AA` / …）、rename / copy 行（`->`）、事前 stage 残り**は **続行せず中断**する（rename は **`git mv` / 別コミット**で解消してから再実行）。ブロック理由には **問題のパス**が表示される。
- **`make codex-review` が書き出す `.ai/reviews/latest.json` の `review_run_status` が `executed`** であることを **必須**とする。次のときは **`commit` / `push` しない**：**Codex CLI 未インストール**（`latest.json` が `skipped` 相当）、**Markdown からの機械 JSON 抽出／スキーマ検証の失敗**（`latest.json` が `failed` または `codex-review` が非ゼロ）、**`latest.json` が欠損・壊損**。**人間向けの本文は `.ai/reviews/latest.md` のみ**。**`safe-push` の判定は `latest.json` のみ**。**通常の `make codex-review` 単体**は CLI 未導入でも案内付き終了コード 0 でよいが、**`safe-push`** は **`review_run_status != executed` を必ずブロック**する。
- **JSON 判定規則**（`scripts/safe_commit_push.sh` → **`.ai/reviews/latest.json` のみ読む**）：`review_run_status != "executed"` → 停止（**`failed` はスキーマ不正・抽出失敗等を意味し、`ALLOW_IMPORTANT=true` でも突破不可**）。**`decision` が `fail`**、または **`critical` が空でない** → 停止。**`needs_human_review` または `important` が空でない** → **原則停止**。**`ALLOW_IMPORTANT=true`** を **人間が明示したときだけ**続行できる（`failed`/`skipped` には適用されない。自動で true にしない）。
- **API Key・実 `.env`・実トークンの投入**、および **live HTTP を本番許可状態にする変更** は **人間専用**。AI が `.env` を生成・編集したり、`JQUANTS_ALLOW_LIVE_HTTP` を勝手に `true` にしたりしない。

詳細：`scripts/codex_review.sh`、`scripts/safe_commit_push.sh`、`Makefile` の `safe-push` / `safe-push-dry-run`。

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
- `make codex-review` / `make ai-check`
- `make ops-check`（live HTTP なし：env 状態の要約、`daily` の J-Quants 抜粋、任意で `gh` による Actions メタ）
- **`SAFE_PUSH_MSG="..." PYTHON=.venv/bin/python make safe-push-dry-run`**（本番の事前確認）または、人間の明示承認がある場合に限り **`SAFE_PUSH_MSG="..." PYTHON=.venv/bin/python make safe-push`**（`scripts/safe_commit_push.sh`：**禁止パス事前検査** → **`make ai-check`** → **`git diff --check`** → **禁止パス再検査** → **`latest.json` 門番** → **候補パスのみ selective** `git add --` / `commit` / `push`）
- `git status --short`
- `git diff --stat`
- `pytest`（またはプロジェクト標準に従ったテスト実行）
- 調査対象が明確な範囲での `cat`（または Read ツールでのファイル読込）

読み取り専用の探索（`grep` / `find` など）はタスクに応じて許可できる。機密ファイルや `outputs/` の実行生成物は**リポジトリにコミットしない**こと（詳細は下記「Git に載せないもの」）。

## 5. AI に禁止するコマンド

以下は**デフォルトで禁止**する（**`make safe-push`** 経由の自動化は別。raw の add/commit/push は不可）。

- `git add`（`scripts/safe_commit_push.sh` 内部を除く）
- `git commit`（同上）
- `git push`（同上）
- `rm` / `rm -rf`
- `.env` の作成・編集・コピー・転載・コミット
- `credentials.json` / `token.json` の作成・編集・コピー・転載・コミット
- `secrets/`、`credentials/` 配下ファイルの同上
- `curl | bash`
- `brew install`
- （その他）外部 API を実キーで叩く操作

## 5.1 ローカル運用ショートカット（DevOps）

- **`make ops-check`**：live HTTP せず **`env-doctor` → `daily-check` → `post-push-check`** を連鎖。**`.env` や API Key の値は表示しない**。`daily-check` は当日レポートから **J-Quants Watchlist Bars Check** を抜粋し簡易リークチェックのみ。
- **`.env` はシェルとして `source` しない**（コマンド置換・バッククォートを走らせない）。`env-doctor` / `daily-check` / `jquants-smoke*` は **`scripts/load_jquants_env.py` が許可 `JQUANTS_*` キーだけ**を読み取り、子プロセス環境へ渡す。
- **`make env-doctor`**：J-Quants 関連の **present / missing / true / false** のみ。**`.env` 全文・実値は出さない**。
- **`make daily-check`**：Python は **`PYTHON=${PYTHON:-.venv/bin/python}`** と同等（Makefile 側の `PYTHON` もそのまま使える）。
- **`make jquants-smoke-dry-run`**：**`DATE=…` `LIMIT=…` 必須**。`debug jquants-watchlist-bars … --save-summary` のみ（**既定 dry-run**。live はしない）。
- **`make jquants-smoke-live`**：**`CONFIRM_LIVE_HTTP=YES` 必須**のうえ、`DATE` / `LIMIT` を渡す。その **1 回の子プロセスだけ** **`JQUANTS_ALLOW_LIVE_HTTP=true`** と **`--live --save-summary`**（人間のみ・運用規約順守）。
- **`make post-push-check`**：**`gh` あり**：最新ワークフローランの **status / conclusion 等のみ**。**なし**：警告して **exit 0**。
- 外部レビュー用のひとつの設計資料：[10_system_overview_for_external_review.md](./10_system_overview_for_external_review.md)

## 6. 標準作業フロー

1. **Cursor** が実装（必要に応じてドキュメント・テストも同時）。
2. ローカルで **`PYTHON=.venv/bin/python make ai-check`**（または CI と揃える `make verify`）。
3. **Codex** がレビューし、人間向け本文が **`.ai/reviews/latest.md`**、機械門番が **`.ai/reviews/latest.json`**（`codex_review.sh` が Markdown 内の **行完全一致**マーカーから抽出・検証したうえで保存）に残る。
4. **承認ゲート**：**`SAFE_PUSH_MSG="..." PYTHON=.venv/bin/python make safe-push`**（**`ALLOW_IMPORTANT=true` は人間が明示したときのみ**。**`Makefile` でメッセージを展開しない**ため **`SAFE_PUSH_MSG` を環境変数で渡す**。**dry-run は `SAFE_PUSH_MSG="..." ... make safe-push-dry-run`**）でコミット／プッシュする。raw の `git commit` / `push` はしない。
5. **GitHub Actions** がグリーンか確認する。

Observation Only・No Auto Trading、`outputs/` 実行生成物の Git 非管理など、プロジェクト規約は常に適用する。

### 6.1 Codex レビューの半自動化（CLI）

手動コピペを減らすため、`codex exec` でレビューを走らせ、**本文を `.ai/reviews/latest.md`、機械判定用に正規化した JSON を `.ai/reviews/latest.json`** に保存するターゲットを用意している。

- **`make codex-review`**  
  - `codex` が PATH に無い場合は **エラー終了とはせず**、`.ai/reviews/latest.md` に案内を書き、**`.ai/reviews/latest.json` に `review_run_status: "skipped"`** を記録して終了コード 0。※**`make safe-push` は `review_run_status != executed` を検出して中断**する。
  - `codex` があるときは **`codex --sandbox read-only --ask-for-approval never exec --ephemeral -C <ROOT>`** で実行し、**全文を `latest.md` に追記**する。
  - `latest.md` 内の **行が完全一致**する `CODEX_REVIEW_JSON_START` / `CODEX_REVIEW_JSON_END` で囲まれたブロックから JSON を取り出し、**複数あればパース＋スキーマ検証に成功した最後のブロック**を採用する。配列に **不正型・null・空文字列** が含まれたブロックは不採用（**黙って要素を捨てない**）。有効なブロックが無い場合は **`latest.json` に `review_run_status: failed`（例: `critical` に `codex_review_json_schema_validation_failed`）を書き、`codex-review` は非ゼロ**で終了する。
  - **`latest.md` / `latest.json` は Git 管理外**（`.gitignore` で `.ai/reviews/*.md` と `.ai/reviews/*.json` を無視）。
  - **`codex` が異常終了**した場合は `make codex-review` が非ゼロとなり、**`latest.json` は `review_run_status: failed`**。**`make ai-check` と `safe-push` はそこで止まる**。
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

関連：[01_development_status.md](./01_development_status.md) · [17_r6_9_parallel_development_prep.md](./17_r6_9_parallel_development_prep.md) · [06_phase0_completion_report.md](./06_phase0_completion_report.md)
