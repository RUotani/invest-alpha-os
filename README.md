## Laputa Alpha OS (InvisAlphaOS / invest-alpha-os)

個人投資家向けの **長期運用型 投資判断支援OS**。

Phase 0-v1.1 は **Observation Only**（執行・発注なし）で、将来の拡張（高品質データ、Shadow Portfolio、Outcome Log、Data Confidence、Hard/Soft Veto、US Watchlist Tier 制）に耐えるプロジェクト骨格を優先して構築します。

### Current Mode

- Current Mode: Observation Only + Shadow Portfolio
- No Auto Trading
- Bot output is for observation and review only during the first 12 weeks
- Do not commit `.env`, `credentials.json`, `token.json`, API keys (including **J-Quants `JQUANTS_API_KEY`**)

### Phase 1a — J-Quants（stub → skeleton → **V2 API Key primary**）

- **既定**: **`JQUANTS_ENABLED=false`**、**`JQUANTS_ALLOW_LIVE_HTTP=false`**、**`JQUANTS_API_BASE_URL` / `JQUANTS_API_KEY` は未設定が既定**。※`make verify`・GitHub Actions・`daily` / `pack` / `risks` は **実接続しない**。
- **Version 2**: **`JQUANTS_API_KEY`** を **`x-api-key`** で送る方式がプライマリ。**実 API Key は Git にコミットしない**（`.gitignore` / `.env` はローカルのみ）。
- **`debug jquants-watchlist-bars`**（Task 6）: `jp_watchlist` を **dry-run / `--preview-request` / `--live`** で一括確認（**`--date` 単独**、または **`--from-date` と `--to-date` のセット**、**`--limit`**）。**4 桁数字のみ wire**、`285A` 等は **skip**。
- **`alpha-os daily`**（Task 7–8）: レポートに **J-Quants Watchlist Bars Check** と **readiness（Green / Yellow / Red）**。**HTTP なし**の **dry-run 集計のみ**。**`make verify` / CI も同様**。
- **ライブ実 HTTP（デバッグのみ）**: **`GET …/equities/bars/daily`** はクエリ **`code` / `date` / `from` / `to`** に対応。CLI は **`--code` / `--date` / `--from-date` / `--to-date`** を任意に指定（日付は **`YYYY-MM-DD`** または **`YYYYMMDD`**）。**API 送信値は公式クイックスタートに合わせ `YYYYMMDD`（Task 5.4）**。**`http_error` 時は `error_body_preview` にマスク済みの短いヒントのみ（Task 5.5、raw 本文は出さない）**。**任意の `JQUANTS_DATA_AVAILABLE_FROM` / `TO` が両方有効なとき、契約外日付は HTTP 前に `validation_error`（Task 5.6）**。**レスポンスの公式前提は `code` または `date` のどちらか**だが、この CLI は **400 切り分けのため `from` または `to` のみ**の送信も許容（**API が受理するかは別**）。まず **`--preview-request` → code-only / date-only**（[09](docs/09_jquants_local_manual_test.md)・Task 5.3〜5.4）。**`--preview-request`** で **送信予定 URL／query のみ**（実 HTTP なし）。**ゲート**：**`JQUANTS_ENABLED` + `--live` + `JQUANTS_ALLOW_LIVE_HTTP=true` + BASE URL + API Key**。欠落時 **`live_blocked` / `not_configured`**。**`HTTP 200` でも**妥当でなければ **`success` にならない**。**`debug jquants-status` は HTTP しない**。
- **Version 1**: **`JQUANTS_API_VERSION=v1`** のときだけ refresh / Bearer による legacy 経路。**閉鎖予定・非推奨**。
- **J-Quants の最小 live smoke test（コード・運用のみ）**: [docs/09_jquants_local_manual_test.md](docs/09_jquants_local_manual_test.md)。**API Key はダッシュボードで人間が取得し、`JQUANTS_API_KEY` と `x-api-key` で送る。Git にコミットせず、Chat／Codex にも貼らない。**
- **実接続（人間のみ・手順）**: 上記 `09`。**通常は `JQUANTS_ALLOW_LIVE_HTTP=false`**。
- **AI Agent に API Key・認証情報を渡さない**。`.env` は人間のみが用意（`.env.example` は変数名のみ）。
- 計画: [docs/08_phase1a_jquants_plan.md](docs/08_phase1a_jquants_plan.md)

### クイックスタート

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
alpha-os --help
```

### Phase 0 の基本コマンド

- `alpha-os status`
- `alpha-os config-check`
- `alpha-os daily`（Markdown 末尾に **J-Quants Watchlist Bars Check**・**readiness**・dry-run のみ）
- `alpha-os pack --ticker 7011`
- `alpha-os risks`
- `alpha-os snapshot watchlist`
- `alpha-os snapshot shadow-portfolio`
- `alpha-os log outcome`
- `alpha-os debug adapters`
- `alpha-os debug jquants-status`（HTTP なし）
- `alpha-os debug jquants-daily-quotes [--code …] [--date …] [--from-date …] [--to-date …] [--preview-request] [--live]`
- `alpha-os debug jquants-watchlist-bars [--date …] [--from-date …] [--to-date …] [--limit N] [--preview-request] [--live]`（Task 6）

### 一括検証

初回セットアップ後の動作確認は、以下のいずれかで実行できます。

- 通常確認コマンド: `make verify`
- 仮想環境を明示する安全な確認コマンド: `PYTHON=.venv/bin/python make verify`
- **`make codex-review`**: `codex exec`（read-only）でレビューし、人間向けを `.ai/reviews/latest.md`、機械門番を `.ai/reviews/latest.json` へ。**`.ai/reviews/*.md` と `.ai/reviews/*.json` は Git 無視**。
- **`make ai-check`**: `make verify` → `codex-review` → `git status`。`Makefile` はデフォルト `PYTHON=python` のとき `.venv/bin/python` があればそちらへ寄せます（明示した `PYTHON=...` は尊重）。

```bash
make verify
```

`make verify` は以下を順番に実行し、エラー時はその場で停止します。

- tests
- status
- config-check
- snapshot watchlist
- daily
- pack --ticker 7011
- risks
- git status --short

### AI 開発運用（Phase 0 完了後）

複数の AI / ツールと協働する際の役割分担と標準フローは [docs/07_ai_development_workflow.md](docs/07_ai_development_workflow.md) を参照してください。

- **`git commit` / `git push`** は **`SAFE_PUSH_MSG="your message" PYTHON=.venv/bin/python make safe-push`** を推奨。**`Makefile` はコミットメッセージをレシピ内で展開せず**、**環境変数 `SAFE_PUSH_MSG`** を **`scripts/safe_commit_push.sh` が検証してから `git commit -m` に渡す**設計です。**`make ai-check`（`verify` + `codex-review`）より前に**、`git status` で **危険パス（`.env` など）を検査**し、該当があれば **レビューも含めて即停止**します。通過後も **再検査**と **`.ai/reviews/latest.json` 門番**、**ステージ後の最終検査**で守ります。**`latest.json` が `failed`/`skipped` は `ALLOW_IMPORTANT` でも突破不可**。**Important** は原則停止（**`ALLOW_IMPORTANT=true`** でのみ人間が続行可）。**raw のその場の `git commit` / `git push` は避ける**。
- **`SAFE_PUSH_MSG="..." PYTHON=.venv/bin/python make safe-push-dry-run`** — commit/push は行わず、追跡差分・ステージ済み・未追跡（除外されないもの）など **Git がコミット候補に含めうるパス**を検査します。実際には `.gitignore` 済みの `.env` は候補に出ずスキャン対象になりません。**Codex JSON 門番も本番同等**です。
- `.env`、`credentials.json`、`token.json`、`outputs/` の実行生成物（実データ）は **Git 管理しない**（セキュリティ節とも整合）。

#### Codex レビュー（半自動）

- **`make codex-review`**: Codex CLI（read-only サンドボックス・非対話）でレビュー。**`.ai/reviews/latest.md` に全文**、続けて **行マーカーで囲んだ JSON を抽出・検証した結果を `.ai/reviews/latest.json`** に保存します。`.env` は参照しない。いずれも **`.gitignore`** で **コミット対象外**。CLI 未インストール時は `latest.md` に案内を書き、`latest.json` は **`review_run_status: "skipped"`**（`make` は exit 0）。
- **`make ai-check`**: **`make verify`** → **`codex-review`** → **`git status --short`**（`PYTHON` は `verify` に明示渡し）。**`codex-review` が非ゼロ終了**（例: Codex 失敗・抽出失敗）**だとそこで止まり、`safe-push` に進みません。**

**`make safe-push`**: **`latest.json` の `review_run_status` が `executed` でない場合**（未導入 `skipped`・失敗 `failed`・欠損）は **commit/push しません**。**機械判定は `latest.json` のみ**です。

### セキュリティ

- **APIキー・token・credentials・`.env` は絶対にコミットしません**（`.gitignore` 済み）。
- データはローカル（`data/`）に保存し、Phase 0 では外部API連携は stub / prototype 扱いです。
- `outputs/` は原則ローカル実行結果として扱い、実データ・個人情報保護のため Git 管理外とします。

