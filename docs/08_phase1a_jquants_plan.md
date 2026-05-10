# Phase 1a — J-Quants 接続計画

## Phase 1a の目的

- 日本株ウォッチリストを **テーマ付きで整理**し、将来のシグナル・日次レポートに載せられる形にする。
- **J-Quants API** を日本株の **primary source 候補**として組み込むための **adapter・設定・環境変数の器**を用意する。
- **Task 1** は stub のみ。**Task 2** で **real-mode skeleton**（`JQuantsClient`）。**Task 3** で **Version2 移行を見据えた設定・ドキュメント**（実接続・正規実装は行わない）。

## Version1 → Version2（重要）

公式ドキュメント上、**Version2 がリリース済み**であり、**Version1 は閉鎖予定**です。そのためコード・設定ともに **「V1 固定 URL」を暗黙のデフォルトにしない**ようにします。

- **`JQUANTS_API_VERSION`**（例: `v2`）で論理バージョンを表す（**実コードは `v1` / `v2` のみ受理**；未知値は `unsupported_version`）。
- **`JQUANTS_API_BASE_URL`** は **公式の Version2 のベース URL を人間が `.env` に設定**する（テンプレート `.env.example` では **空のまま**。CI でも未設定で **実 HTTP に進めない**）。
- コード内の相対パスは **`api_version` ごとのテーブル**（`_paths_for_version`）にまとめ、**Task 4** で公式 v2 のパス確定後にここだけ差し替えやすくする。
- 「旧 V1」のパス説明が必要な箇所は歴史的参考に留め、**現行運用は v2 とドキュメント照合前提**とする。

## J-Quants 接続の段階設計

| 段階 | 内容 |
|------|------|
| **Task 1** | `JQuantsStubAdapter`、`jp_equity`、`watchlist`、`.env.example`、daily **Japan Signals**（stub） |
| **Task 2** | `JQuantsClient`（認証・`daily_quotes` の内部 HTTP 骨格）。**`debug jquants-status` は HTTP 禁止**。**実 HTTP** は `debug jquants-daily-quotes --live` **かつ** **`JQUANTS_ALLOW_LIVE_HTTP=true`** の **二重ゲート**のみ |
| **Task 3** | **ローカル手動接続ガイド**（[09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md)）、`config/market_data.yaml` の jquants メタ、`JQUANTS_API_VERSION` / `JQUANTS_API_BASE_URL` 対応、`safe_auth_status` 拡張。**このタスクでは実 API 接続や正規レスポンス処理は行わない** |
| **Task 3.1** | **安全強化**: `JQUANTS_API_VERSION` を **`v1` / `v2` のみ許可**（それ以外は `unsupported_version`・**実 HTTP なし**）。**`JQUANTS_API_BASE_URL` 未設定時はライブ許可があっても `not_configured`（`base_url_missing`）**。CLI / テストで回帰を防ぐ |
| **Task 4 以降** | 公式 **Version2** 仕様の確定確認、エンドポイント・レスポンス正規化、キャッシュ・レート制限、トークン期限の自動更新、本格的な実接続テスト |

### Task 2 で追加したこと（要約）

- **`safe_auth_status()`**: プレゼンスフラグと `token_preview: "***"` のみ（**トークン実値・パスワード・raw を出さない**）。
- **`JQuantsClient`**: 公開戻り値に **refresh / id 実値・raw JSON を含めない**。ライブチェーンで得た機密は **メモリ内のみ**。
- **`debug jquants-status`**: **プローブ無し**。標準出力に秘密を載せない。
- **`debug jquants-daily-quotes`**: 既定 **dry-run**。`**--live` + `JQUANTS_ALLOW_LIVE_HTTP=true`** のときのみ実 HTTP を試行。
- **`make verify` / `daily` / `pack` / `risks`**: **変更なしで J-Quants へ接続しない**。CI と同様。

### Task 3 で追加したこと（要約）

- **[09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md)** — 人間向けローカル手動確認、二重ゲート、トラブルシュート。
- **`JQUANTS_API_BASE_URL` 未設定時**はネットワークを伴う処理を **`not_configured`**（**`reason: base_url_missing`**）で止める（フォールバック固定 URL なし）。**`JQUANTS_ALLOW_LIVE_HTTP=true` かつ `--live` が付いていても同様**。
- **`safe_auth_status()`** に **`api_version` / `api_version_effective` / `unsupported_api_version` / `base_url_present` / `allow_live_http`** を明示。
- **`config/market_data.yaml`** に `api_version`、`base_url_env`、`ci_live_http: disabled`、`manual_live_http: double_gate_required` 等。

### Task 3.1 で追加したこと（安全強化）

- **`JQUANTS_API_VERSION` 厳格化**: 許可は **`v1` / `v2`（および定義済みエイリアス）のみ**。それ以外は **`unsupported_version`** 応答とし、**urllib による実 HTTP を実行しない**。
- **`debug jquants-status`**: `unsupported_api_version` / `api_version_effective` を表示（**秘密は出さない**）。
- **テスト**: `base_url` 未設定かつ **full live 意図**でも `urlopen` が呼ばれないこと、未知 version でも HTTP しないことを明示。

### ライブ HTTP の前提（Codex / 安全運用）

- **`JQUANTS_ENABLED=true`** は必要だが **それ単体では不十分**。**`--live`** と **`JQUANTS_ALLOW_LIVE_HTTP=true`** を **両方**満たすこと。
- さらに **`JQUANTS_API_BASE_URL`** が **非空**で、**`JQUANTS_API_VERSION` が `v1` / `v2` に解決できる**こと、が前提（Task 3.1）。
- 認証情報は **GitHub Secrets に置かず**、**ローカル `.env` のみ**（運用規約）。

### 認証・エンドポイント（参考・Task 4 で v2 に同期）

歴史的に V1 では次のようなイメージが知られているが、**Version2 では URL・パス・ペイロードが変わる可能性がある**。実装は `_paths_for_version` を公式仕様で更新すること。

- メールログイン → refresh
- refresh → id（Bearer）
- daily quotes 等を GET

## 認証情報を Git に載せない方針

- **実メール・パスワード・refresh / id トークン**は **`.env` にのみ**置く（**Git にコミットしない**）。
- **`.env.example` には変数名だけ**。**実値を書かない**。
- **`JQUANTS_ID_TOKEN` / `JQUANTS_REFRESH_TOKEN` は期限付き**。失効時は再取得または refresh。運用では期限とローテーションをドキュメント化する。

## API キーなしでも stub で動く方針

- **`JQUANTS_ENABLED=false`**（既定）では `JQuantsStubAdapter` / `JQuantsClient` ともに **ネットワークに出ない**経路のみ。
- **GitHub Actions** でも **Secrets を使わず**、**実接続は行わない**（`config/market_data.yaml` の `ci_live_http: disabled` と整合）。

## 将来取得したいデータ（J-Quants API）

- `listed/info`
- `prices/daily_quotes`
- `fins/statements`
- `fins/announcement`

## AI / 開発者向け注意

- **AI Agent にメール・パスワード・トークンを渡さない**（[07_ai_development_workflow.md](./07_ai_development_workflow.md)）。
- 実接続を試す場合は **[09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md)** に従い、**ローカルのみ**で人間が実施する。

---

関連: [09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md) · [07_ai_development_workflow.md](./07_ai_development_workflow.md) · [06_phase0_completion_report.md](./06_phase0_completion_report.md)
