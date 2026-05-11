# J-Quants ローカル手動接続確認（人間のみ）

## 目的

**人間**が自分の環境だけで J-Quants への接続可否を確認するためのチェックリストと手順です。  
自動化された CI や AI エージェントが実 API を叩く用途ではありません。

## 前提（必読）

1. **API Key は [J-Quants のダッシュボード等で人間が取得する](./08_phase1a_jquants_plan.md)**。自動化された取得は想定しない。
2. **`.env` は人間だけが作る**。AI／エージェントはリポジトリに `.env` を追加・編集しない（[07_ai_development_workflow.md](./07_ai_development_workflow.md)）。
3. **ChatGPT・Cursor・Codex などのチャットに API Key・メール・パスワード・refresh/id トークンを貼らない**。スクリーンショットに載せない。
4. **`JQUANTS_ENABLED=true` だけでは実 HTTP は走らない。** さらに次を **すべて**満たす必要があります。
   1. `JQUANTS_ENABLED=true`
   2. `JQUANTS_ALLOW_LIVE_HTTP=true`
   3. `alpha-os debug jquants-daily-quotes ... --live`（CLI で live 意図）
   4. **`JQUANTS_API_BASE_URL` が非空**
   5. **（V2 既定）`JQUANTS_API_KEY` が非空**（リクエストは **`x-api-key`** ヘッダー。**実値はチャットにも CLI 出力にも出さない**。）
5. **`alpha-os debug jquants-status` は常に HTTP しない**（`safe_auth_status()` のみ。プレビューは `***`）。
6. **GitHub Actions / `make verify` は J-Quants に live 接続しません**。ローカルの手確認だけが対象です。
7. Version2 がプライマリ（`GET /v2/equities/bars/daily` は **API Key・`x-api-key`**）。**`JQUANTS_API_VERSION`** / **`JQUANTS_API_BASE_URL`** は公式に合わせて人間が設定する（詳細は [08_phase1a_jquants_plan.md](./08_phase1a_jquants_plan.md)）。
8. **`JQUANTS_API_VERSION` は `v1` と `v2`（および定義済みエイリアス）のみ**。それ以外は **`unsupported_version`** → 実 HTTP なし（`unsupported_api_version` を `jquants-status` で確認）。
9. **`JQUANTS_API_BASE_URL` が空** のままでは **`not_configured` / `base_url_missing`**。
10. **（V2）`JQUANTS_API_KEY` が空** では **`not_configured` / `api_key_missing`**。
11. **`debug jquants-daily-quotes` と終了コード**：
    - **`--preview-request`**：**送信プレビュー（秘密なし）のみ**。**HTTP は行わない** → **`exit 0`**（プレビューオブジェクトの **`status`** が `unsupported_version` / `not_configured` 等でも **ネットワークは使わない**）。
    - **`--live` なし**：**dry-run**（実 HTTP なし）→ 原則 **`exit 0`**。標準出力は **`status` / `code` / `date_from` / `date_to`** と、利用可能なら **`query_params` / `full_url_without_secrets`**（および `endpoint`）程度。**raw 応答・API Key 値・ヘッダー全体は出ない**。
    - **`--live` あり**でゲート不足・検証失敗は **`exit 1`**（例: `live_blocked`、`not_configured`、`unsupported_version`、`disabled`、 **`non_json_response` / `invalid_response`**）。
    - **`--live` あり**で HTTP 成功かつレスポンス正規化 **`success`**（下記 Phase 5）→ **`exit 0`**。
12. **`make verify` / CI は `--live` を使わない**。
13. **最小 live smoke**：**1 銘柄・短期間のみ**。**推奨コード例**：`70110` または `86970`。**日付**：公式サンプル・取得可能レンジに合わせる（営業日・データ公開の遅延に留意）。
14. **日付・クエリ（Task 5.1）**：CLI では **`--from-date` / `--to-date`**（人間向け）を使う。V2 のライブ HTTP では公式どおりクエリ名 **`from` / `to`**（および必要なら **`date`**）に変換し、値は **`YYYY-MM-DD`** で送る。**`from_date` や `to_date` というクエリ名は使わない**。**HTTP 400** のときは、まず **`--preview-request`**（Task 5.2）で送信内容を確認したうえで、パラメータ名・証券コード形式・日付形式を疑う。
15. **`--preview-request`（Task 5.2）**：**実 HTTP は行わない**（`JQUANTS_ALLOW_LIVE_HTTP=true` でも **プレビューのみなら urlopen しない**）。**`full_url_without_secrets` / `query_params` / `endpoint_url_without_query`** を表示し、**API Key 実値・raw body・ヘッダー全体は表示しない**。

### 応答検証（Task 5：`normalize_v2_daily_bars_response`）

ライブ応答ボディが **JSON オブジェクト**であっても、次の **`data` / `daily_quotes` / `bars` / `results` の順に最初に見つかったキー**の値が **配列であること** が必須です。

- **`status`: `success`**：上記キーのいずれかが **配列**。**`row_count`** はその配列長。**空配列 `[ ]` の場合も `success` で `row_count=0`**（通信は成功しているがヒット行がない）。
- **`invalid_response`**：トップレベル配列、オブジェクトだが一覧キー欠如、一覧キーの値が **dict / str / 数値など list 以外**（例：`{"message": "error"}` のみ）。
- **`non_json_response`**：ボディが JSON オブジェクトとして解釈できない。

CLI の `--live` 成功時でも **OHLC などの銘柄行データは標準出力に出さず**、`row_count` / `source_key` のみ伝える。

---

## 手順概要

### 1. `.env` の作成（人間のみ）

`.env.example` を参照し、**人間がローカルでのみ** `.env` を用意する。**このドキュメントやチャットに実値を書かない。**

### 2. 設定の確認

- **`JQUANTS_API_VERSION`** — **`v2` 推奨**。**`v1` は legacy**。
- **`JQUANTS_API_KEY`** — **V2 live で必須**。**チャットへ貼らない**。
- **`JQUANTS_API_BASE_URL`** — 公式の **Version2 のベース URL**。
- **`JQUANTS_ENABLED=true`**、**`JQUANTS_ALLOW_LIVE_HTTP=true`**（確認中のみ）。
- メールログイン〜トークン列は **`JQUANTS_API_VERSION=v1` の legacy のみ**。

### 3. HTTP しない確認（任意）

```bash
alpha-os debug jquants-status
```

表示に **API Key・トークン・パスワード・raw が含まれない**ことを確認する。

### 4. Live smoke（自己責任・プレースホルダのみここに記載）

チャット／ドキュメントに **実 API Key と実ベース URL を書かない**。ローカルの `.env` または自分の環境のみでセットする。

```bash
export JQUANTS_ENABLED=true
export JQUANTS_ALLOW_LIVE_HTTP=true
# （人間のみ）ダッシュボードで取得した API Key と公式 BASE URL を自分の環境で設定済みであること。
# export JQUANTS_API_BASE_URL="https://REPLACE_WITH_OFFICIAL_V2_BASE/"
# export JQUANTS_API_KEY="REPLACE_WITH_YOUR_KEY"
alpha-os debug jquants-daily-quotes \
  --code REPLACE_WITH_CODE_OR_70110_OR_86970 \
  --from-date YYYY-MM-DD \
  --to-date YYYY-MM-DD \
  --live
```

**実行後すぐ**：**`JQUANTS_ALLOW_LIVE_HTTP=false`** に戻す（`unset JQUANTS_ALLOW_LIVE_HTTP` または `.env` で明示）。普段は live をオフに保つ。

---

## トラブルシュート

### `invalid_response`

- **`reason`: `*_not_list`**：`data` 等が配列になっていない（API エラーボディをオブジェクトで返している等）。
- **`reason`: `missing_list_field`**：期待する一覧キーがどれもない（例：`message` のみ）。
- **live の成功と誤認しない**：`exit 1` を確認する。

### `non_json_response`

- HTML／プレーン文字列応答。**HTTP コードが良くても** `success` にはならない。

### 空結果（**`success` で `row_count=0`**）

- ヒットしない日付・コード形式・休場。**エラーとは限らない**。公式のコード桁・クエリ規約と照らす。

### HTTP 400 と `status: http_error`

1. **`alpha-os debug jquants-daily-quotes … --preview-request`** で **送信予定の **`query_params`・`full_url_without_secrets`**（**API Key 実値・raw・ヘッダー全体なし**）を確認する。`**--preview-request` は HTTP をしない**（`JQUANTS_ALLOW_LIVE_HTTP=true` でも同様）。
2. **`full_url_without_secrets`** に **`/v2/v2/` が含まれていないか**確認する（ベース URL に `/v2` があるときの誤結合ガード）。
3. **`query_params` が `code` / `from` / `to`（必要なら `date`）**になっているか、**`from_date` / `to_date` が混入していないか**確認する。
4. それでも 400 の場合は **証券コードの形式・日付フォーマット・プラン権限・提供データ範囲**などを公式に照合する。

**`--live` で `http_error` になったとき**の CLI は **`status` / `http_status` / 銘柄 `code` / `date_from` / `date_to` と、上記と同種の送信プレビュー（秘密なし）**を **`raw_response_included: false`** のまま出力する。**API Key の値・応答ボディは出ない**。
- **`--from-date` / `--to-date`** は内部で **`from` / `to`** クエリに変換し、値は **`YYYY-MM-DD`**（Task 5.1）。

### 401 / 403（認証）

- **`x-api-key`** と Key の対応、Key の期限・無効化を確認する。

---

## 関連ドキュメント

- [08_phase1a_jquants_plan.md](./08_phase1a_jquants_plan.md) — Phase 1a・Version2・タスク一覧
- [07_ai_development_workflow.md](./07_ai_development_workflow.md) — AI 運用・禁止事項
- [README.md](../README.md) — CLI 一覧と概要
