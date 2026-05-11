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
    - **`--preview-request`**：**送信プレビュー（秘密なし）のみ**。**HTTP は行わない**。**CLI 側の入力検証**（いずれの条件も無い、`--date` と `--from`/`--to` の併用など）では **`validation_error`** → **`exit 1`**。**それ以外**でプレビューオブジェクトを出す場合は原則 **`exit 0`**（`unsupported_version` 等でも **ネットワークは使わない**）。
    - **`--live` なし**：**dry-run**（実 HTTP なし）→ **`validation_error`** でない限り **`exit 0`**。標準出力は **`status` / `code` / `date` / `date_from` / `date_to`**（省略時は `null`）と、利用可能なら **`query_params` / `full_url_without_secrets`**（および `endpoint`）。**raw 応答・API Key 値・ヘッダー全体は出ない**。
    - **`--live` あり**でゲート不足・検証失敗は **`exit 1`**（例: `live_blocked`、`not_configured`、`unsupported_version`、`disabled`、 **`non_json_response` / `invalid_response`**。※**CLI 入力の検証エラー**（`missing_all_of_code_date_from_to` 等）は **`get_daily_quotes` に達する前に** **`exit 1`**。
    - **`--live` あり**で HTTP 成功かつレスポンス正規化 **`success`**（下記 Phase 5）→ **`exit 0`**。
12. **`make verify` / CI は `--live` を使わない**。
13. **最小 live smoke**：**1 銘柄・短期間のみ**。**推奨コード例**：`70110` または `86970`。**日付**：公式サンプル・取得可能レンジに合わせる（営業日・データ公開の遅延に留意）。
14. **日付・クエリ（Task 5.1 + 5.3 + 5.4）**：CLI では **`--code` / `--date` / `--from-date` / `--to-date`** を組み合わせる（日付は **`YYYY-MM-DD`** または **`YYYYMMDD`** を入力可。**カレンダー無効**は **`validation_error` / `invalid_date_format`**）。**いずれの条件も無い**と **`validation_error`**。**`--date` と `--from-date`/`--to-date` は排他**。V2 の API 送信ではクエリ名 **`code` / `date` / `from` / `to`** のみで、**値は公式クイックスタートに合わせて `YYYYMMDD`（ハイフンなし 8 桁）**（**`from_date` / `to_date` というクエリ名は使わない**）。**`--preview-request`** の **`query_params` / `full_url_without_secrets` は実 HTTP と同じ形式**（例：`date=20260508`）。**応答側の公式前提は「`code` または `date` のどちらか」だが、この CLI は切り分けのため、`from` または `to` の片方だけ**を載せたリクエストも許容する（**HTTP 400 になり得る**）。レンジは **`from` と `to` の両方そろえることを推奨**。**HTTP 400** のときは、このドキュメントの **「HTTP 400 と `status: http_error`」** に従って切り分ける。
15. **`--preview-request`（Task 5.2）**：**実 HTTP は行わない**（`JQUANTS_ALLOW_LIVE_HTTP=true` でも **プレビューのみなら urlopen しない**）。**`full_url_without_secrets` / `query_params` / `endpoint_url_without_query`** を表示し、**API Key 実値・raw body・ヘッダー全体は表示しない**。**`query_params` の日付は `YYYYMMDD`（Task 5.4）**。

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

公式の `GET …/equities/bars/daily` では **`code` または `date` のどちらかが必須**です。CLI では **`--code` / `--date` / `--from-date` / `--to-date` はすべて任意**で、**そのいずれも指定がない**と **`validation_error`**（`missing_all_of_code_date_from_to`）で HTTP に進みません。**`--date`** と **`--from-date` または `--to-date` は同時に指定しない**でください（`date_mutually_exclusive_with_from_to`）。日付レンジを使う場合は **`from` と `to` の両方を揃えることを推奨**しますが、CLI としては **`from` または `to` の片方だけ**もクエリに乗せられます。**API Key の実値や応答本文の生データは出しません**が、**`http_error` 時**は **`error_body_preview`**（**短縮・マスク済み**、Task 5.5）で理由のヒントのみ表示します（**JSON で `message` 等がない応答では項目自体が省略される**こともあります）。それ以外のプレビューは **`full_url_without_secrets`** と **`query_params`** のみ。

#### ChatGPT 等に貼る場合

- 共有してよい例：**`status`** / **`http_status`** / **`error_body_preview`** / **`query_params`** のみ。
- **API Key・トークン・パスワード・raw 応答本文・`.env` の実値は貼らない**。

#### HTTP 400 の切り分け順（Task 5.3）

1. **`alpha-os debug jquants-daily-quotes --preview-request …`** で送る URL を確認する（**HTTP は行わない**。**API Key 実値・raw は出ない**）。
2. **`--code 7011` のみ**（code-only）。
3. **`--code 7203` のみ**（別銘柄の code-only）。
4. **`--date YYYY-MM-DD` のみ**（date-only）。
5. **`--code 7011 --date YYYY-MM-DD`**（code + date）。
6. **`--code 7011 --from-date … --to-date …`**（code + range。`query` 名は **`from` / `to`**）。
7. **`--live` 実行後**、標準出力の **`error_body_preview`** を確認する（**Task 5.5**・**マスク済み・短縮済み**。**raw 本文や API Key は貼らない**）。

共通確認:

1. **`query_params` が `code` / `date` / `from` / `to` の公式名だけ**で、**日付の値が `YYYYMMDD`（8 桁）**になっているか。**`from_date` / `to_date` / `date_from` / `date_to` が混ざっていないか**。
2. **`full_url_without_secrets`** に **`/v2/v2/` が含まれていないか**（ベース URL に `/v2` があるときの誤結合ガード）。

それでも 400 の場合は **まず日付形式**（プレビューで **`date` / `from` / `to` が `YYYYMMDD` か**）、**対象日が営業日・データ公開があるか**、**証券コード形式**、**プラン・権限**を公式情報と照合する。

**`--live` で `http_error` になったとき**の CLI は **`status` / `http_status` / `error_body_preview`（あれば）** / **`code` / `date` / `date_from` / `date_to`** と、送信プレビュー（**`query_params` / `full_url_without_secrets`**）を **`raw_response_included: false`** のまま出力する。**完全なエラー本文は返しません**（プレビューのみ）。
- **`--date` / `--from-date` / `--to-date`** は CLI では読みやすい形でも指定できるが、**V2 のクエリ値は `YYYYMMDD` に正規化されて送られる**（Task 5.4）。

### 401 / 403（認証）

- **`x-api-key`** と Key の対応、Key の期限・無効化を確認する。

---

## 関連ドキュメント

- [08_phase1a_jquants_plan.md](./08_phase1a_jquants_plan.md) — Phase 1a・Version2・タスク一覧
- [07_ai_development_workflow.md](./07_ai_development_workflow.md) — AI 運用・禁止事項
- [README.md](../README.md) — CLI 一覧と概要
