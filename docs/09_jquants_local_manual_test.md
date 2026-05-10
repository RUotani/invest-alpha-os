# J-Quants ローカル手動接続確認（人間のみ）

## 目的

**人間**が自分の環境だけで J-Quants への接続可否を確認するためのチェックリストと手順です。  
自動化された CI や AI エージェントが実 API を叩く用途ではありません。

## 前提（必読）

1. **AI Agent（Cursor 等）に、API Key・メール・パスワード・refresh/id トークンを渡さない**（[07_ai_development_workflow.md](./07_ai_development_workflow.md)）。
2. 認証情報は **ローカルの `.env` にのみ**置く。**`.env` は人間のみが作成**し、Git 管理外とする。テンプレートは **[.env.example](../.env.example)** の変数名のみを参照する。
3. **`JQUANTS_ENABLED=true` だけでは実 HTTP は走らない。** さらに次を **すべて**満たす必要があります。
   1. `JQUANTS_ENABLED=true`
   2. `JQUANTS_ALLOW_LIVE_HTTP=true`
   3. `alpha-os debug jquants-daily-quotes ... --live`（CLI で live 意図）
   4. **`JQUANTS_API_BASE_URL` が非空**
   5. **（V2 既定）`JQUANTS_API_KEY` が非空**（リクエストは **`x-api-key`** ヘッダー。**実値は CLI に出力されない設計**。）
4. **`alpha-os debug jquants-status` は常に HTTP しない**（`auth_method`、`api_key_present`、`token_preview` / `api_key_preview` が `***` のプレゼンスのみ）。
5. **GitHub Actions / `make verify` は実 J-Quants に接続しません**。ローカルの手確認だけが対象です。
6. API は **公式の Version2 への移行**が進んでおり、Version1 は閉鎖予定です。**`JQUANTS_API_VERSION`** と **`JQUANTS_API_BASE_URL`** は公式ドキュメントに合わせて人間が設定してください（詳細は [08_phase1a_jquants_plan.md](./08_phase1a_jquants_plan.md)）。
7. **`JQUANTS_API_VERSION` はコード上 `v1` と `v2`（`1` / `version1` 等のエイリアス含む）のみ有効**です。それ以外は **`unsupported_version`** となり、**実 HTTP は実行されません**（`debug jquants-status` の `unsupported_api_version` を確認）。
8. **`JQUANTS_API_BASE_URL` が空のままでは、`JQUANTS_ALLOW_LIVE_HTTP=true` かつ `--live` が付いていても実 HTTP しません**（`not_configured` / `reason: base_url_missing`）。
9. **（V2）`JQUANTS_API_KEY` が空のままでは、上記ゲートが揃っていてもライブ実 HTTP は行いません**（`not_configured` / `reason: api_key_missing`）。
10. **`debug jquants-daily-quotes` と終了コード（Task 4.1）**: **`--live` を付けた場合**、実 HTTP がブロックされているときは **`exit 1`**。例:`status` が **`live_blocked`**（例: `JQUANTS_ALLOW_LIVE_HTTP=false`）、**`not_configured`**（`base_url_missing` / `api_key_missing` を含む）、**`unsupported_version`**、**`disabled`**（`JQUANTS_ENABLED=false` のまま live を試したとき）、検証・通信失敗系（**`failed` / `http_error` / `error` / `non_json_response` / `invalid_response`** など）。**`--live` なし**の dry-run・`disabled` の通常表示・`dry_run` 成功は従来どおり **`exit 0`**（**`make verify` / CI は `--live` を使わない**ため影響なし）。
11. **`exit 0`** は **「dry-run が成功して表示できた」**または **「`--live` で `status":"success"`（ライブの API レイヤでは成功）」**を意味する。どちらかは標準出力 JSON の **`status`** と **`--live` の有無**で区別する。**`live_blocked` は安全停止であり、接続の成功とはみなされません**。
12. **`--live` 時の応答検証（Task 4.2）**: **`HTTP 200` や「通信が繋がった」だけでは `success` とみなしません。** レスポンスは **JSON のオブジェクト**であり、本体候補として **`daily_quotes` / `bars` / `data` / `results` のいずれかのキーを含む**最小構造を満たした場合のみ、`get_daily_quotes` の結果が **`status":"success"`** になり得ます。**`non_json_response`**（ボディが JSON として解釈できない）は **HTTP とは別次元の検証失敗**です。**`invalid_response`**（トップレベル配列、期待キー不足など）は **レスポンス形の検証失敗**であり、**ライブ接続そのものが成功した意味ではありません**。**Task 5** で公式 Version2 の形に合わせた正規化・検証をさらに強化する予定です。

## 手順概要

### 1. `.env` の作成（人間のみ）

`.env.example` をコピーして `.env` を作成します（例）。

```bash
cp .env.example .env
```

実 API Key・パスワード・トークンなどの**入力は、このドキュメントやチャットには書かず**、ローカルのエディタでだけ行ってください。

### 2. 設定の確認

推奨（テンプレートに沿う場合）：

- **`JQUANTS_API_VERSION`** — **`v2` を推奨**。**`v1` は legacy**。未対応の値は **`unsupported_api_version`**。
- **`JQUANTS_API_KEY`** — **V2 でライブには必須**。**AI へ渡さない**。CLI は実値を出さず **`api_key_present` と `***` のみ**。
- **`JQUANTS_API_BASE_URL`** — 公式の **V2 ベース URL**。空では **`reason: base_url_missing`** で止まる。
- **`JQUANTS_ENABLED=true`** — デバッグでの有効化。
- **`JQUANTS_EMAIL` … `JQUANTS_ID_TOKEN`** — **`v1` legacy** のみで使用する想定。

### 3. HTTP しない確認（任意）

状態だけ見る場合（**ネットワークなし**）。

```bash
alpha-os debug jquants-status
```

表示に **API Key・トークン・パスワード・raw が含まれない**ことを確認してください（プレフィールドはすべてマスク）。

### 4. 実 HTTP（ゲート複合・自己責任・V2 前提）

**接続確認が必要なときだけ**、`JQUANTS_ENABLED=true`、`JQUANTS_ALLOW_LIVE_HTTP=true`、`--live` に加え、**有効な `JQUANTS_API_BASE_URL`** と **`JQUANTS_API_KEY`** をセットしたうえで実行します。

```bash
# 値はすべてローカル .env で設定する。このブロックには実 API Key や実 URL を書かないこと。
export JQUANTS_ENABLED=true
export JQUANTS_ALLOW_LIVE_HTTP=true
# export JQUANTS_API_BASE_URL="(公式どおりにベース URL を自分の環境で設定)"
# export JQUANTS_API_KEY="(V2 の API Key を自分の環境で設定)"
alpha-os debug jquants-daily-quotes --code 7011 --from-date YYYY-MM-DD --to-date YYYY-MM-DD --live
```

欠けている項目があると **`live_blocked`** または **`not_configured`（`api_key_missing` / `base_url_missing`）** となり **実 HTTP しません**。

確認が終わったら **必ず戻してください**：

```bash
unset JQUANTS_ALLOW_LIVE_HTTP
# または .env で JQUANTS_ALLOW_LIVE_HTTP=false
```

---

## トラブルシュート

### 401 / 403（認証・権限）

- **V2**: **`JQUANTS_API_KEY`** が `.env` に正しく入っているか、**ヘッダー `x-api-key`** で送られることを公式手順と照合する。**キーを再発行したら古い値を削除**する。
- **V1 legacy**: メールログインまたは refresh / id トークンが有効か確認する。**トークン期限**にも注意する。

### トークン期限

- id token は短命であることが多いです。**refresh が有効なら**公式の refresh フローを利用し、無効ならメールログインから取り直す。
- アプリ側は **ログに実トークンを出さない**設計です。デバッグ時も **環境変数をチャットやスクリーンショットに載せない**。

### `date` / `from_date` / `to_date`

- CLI・API が要求する **日付フォーマット**（`YYYY-MM-DD` と YYYYMMDD の違い等）が公式どおりか確認する。
- 休場日・データ未公開日はレスポンスが空になることがある（エラーとは限らない）。

### 銘柄 `code` 形式

- 公式が求める証券コード形式（桁・プレフィックス）に合わせる。一覧 API でコード体系を確認する。

### レート制限 / ネットワークエラー

- 短時間に大量リクエストしない。エラー時はしばらく待ってから再試行する。
- 企業ネットワーク・VPN・プロキシで API ドメインがブロックされていないか確認する。

---

## 関連ドキュメント

- [08_phase1a_jquants_plan.md](./08_phase1a_jquants_plan.md) — Phase 1a・Version2 移行の計画
- [07_ai_development_workflow.md](./07_ai_development_workflow.md) — AI 運用・禁止事項
- [README.md](../README.md) — CLI 一覧と概要
