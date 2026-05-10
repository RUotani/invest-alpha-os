# J-Quants ローカル手動接続確認（人間のみ）

## 目的

**人間**が自分の環境だけで J-Quants への接続可否を確認するためのチェックリストと手順です。  
自動化された CI や AI エージェントが実 API を叩く用途ではありません。

## 前提（必読）

1. **AI Agent（Cursor 等）にメール・アドレス・パスワード・refresh/id トークンを渡さない**（[07_ai_development_workflow.md](./07_ai_development_workflow.md)）。
2. 認証情報は **ローカルの `.env` にのみ**置く。**`.env` は Git 管理外**で、テンプレートは **[.env.example](../.env.example)** の変数名のみを参照する。
3. **`JQUANTS_ENABLED=true` だけでは実 HTTP は走らない。** 実ネットワーク呼び出しには次の **二重ゲート** が必須です。  
   - CLI: `alpha-os debug jquants-daily-quotes ... --live`  
   - 環境変数: `JQUANTS_ALLOW_LIVE_HTTP=true`
4. **`alpha-os debug jquants-status` は常に HTTP しない**（状態フラグのみ）。トークン・パスワード・raw response は **`token_preview` などマスク済みのプレゼンス情報のみ**です。
5. **GitHub Actions / `make verify` は実 J-Quants に接続しません**。ローカルの手確認だけが対象です。
6. API は **公式の Version2 への移行**が進んでおり、Version1 は閉鎖予定です。**`JQUANTS_API_VERSION`** と **`JQUANTS_API_BASE_URL`** は公式ドキュメントに合わせて人間が設定してください（詳細は [08_phase1a_jquants_plan.md](./08_phase1a_jquants_plan.md)）。
7. **`JQUANTS_API_VERSION` はコード上 `v1` と `v2`（`1` / `version1` 等のエイリアス含む）のみ有効**です。それ以外は **`unsupported_version`** となり、**実 HTTP は実行されません**（`debug jquants-status` の `unsupported_api_version` を確認）。
8. **`JQUANTS_API_BASE_URL` が空のままでは、`JQUANTS_ALLOW_LIVE_HTTP=true` かつ `--live` が付いていても実 HTTP しません**（`not_configured` / `reason: base_url_missing`）。

## 手順概要

### 1. `.env` の作成（人間のみ）

`.env.example` をコピーして `.env` を作成します（例）。

```bash
cp .env.example .env
```

実メール・パスワード・トークンの**入力は、このドキュメントやチャットには書かず**、ローカルのエディタでだけ行ってください。

### 2. 設定の確認

推奨（テンプレートに沿う場合）：

- **`JQUANTS_API_VERSION`** — **`v1` または `v2`**（エイリアス可）。**未対応の値は実接続不可**（`alpha-os debug jquants-status` で `unsupported_api_version` を確認）。
- **`JQUANTS_API_BASE_URL`** — **公式 API ガイドを確認したうえで**セット。空のままでは **`not_configured`（`reason: base_url_missing`）** とし、ライブ許可があっても **実 HTTP は行いません**。
- **`JQUANTS_ENABLED=true`** — デバッグ CLI で「有効」扱いにする場合など。
- 認証には **`JQUANTS_EMAIL` / `JQUANTS_PASSWORD`** と、または **`JQUANTS_REFRESH_TOKEN` / `JQUANTS_ID_TOKEN`** の運用があります（どちらを使うかは公式フローに従う）。

### 3. HTTP しない確認（任意）

状態だけ見る場合（**ネットワークなし**）。

```bash
alpha-os debug jquants-status
```

表示に **実トークン・パスワード・raw は含まれない**ことを確認してください。

### 4. 実 HTTP（二重ゲート・自己責任）

**接続確認が必要なときだけ**、一時的に `JQUANTS_ALLOW_LIVE_HTTP=true` を付与し、`--live` でデバッグコマンドを実行します。

```bash
export JQUANTS_ALLOW_LIVE_HTTP=true
alpha-os debug jquants-daily-quotes --code 7011 --from-date YYYY-MM-DD --to-date YYYY-MM-DD --live
```

確認が終わったら **必ず戻してください**：

```bash
unset JQUANTS_ALLOW_LIVE_HTTP
# または .env で JQUANTS_ALLOW_LIVE_HTTP=false
```

---

## トラブルシュート

### 401 / 403（認証・権限）

- メール・アドレスとパスワード、または refresh / id トークンが正しいか、**公式の認証手順**と照合する。
- **トークン期限切れ**の可能性（下記）。再取得して `.env` を更新する。
- **`JQUANTS_API_BASE_URL` / `JQUANTS_API_VERSION`** が公式の Version2 向け URL・パスと一致しているか確認する。

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
