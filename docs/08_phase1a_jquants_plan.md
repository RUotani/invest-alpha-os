# Phase 1a — J-Quants 接続計画

## Phase 1a の目的

- 日本株ウォッチリストを **テーマ付きで整理**し、将来のシグナル・日次レポートに載せられる形にする。
- **J-Quants API** を日本株の **primary source 候補**として組み込むための **adapter・設定・環境変数の器**を用意する。
- **Task 1** では stub のみ。**Task 2** で **real-mode skeleton**（`JQuantsClient`）を追加し、**実 HTTP は明示的な debug CLI のみ**で可能にする。

## J-Quants 接続の段階設計

| 段階 | 内容 |
|------|------|
| **Task 1** | `JQuantsStubAdapter`、`jp_equity`、`watchlist`、`.env.example`、daily **Japan Signals**（stub） |
| **Task 2** | `JQuantsClient`（認証・`daily_quotes` の内部 HTTP 骨格）。**`debug jquants-status` は HTTP 禁止**。**実 HTTP** は `debug jquants-daily-quotes --live` **かつ** **`JQUANTS_ALLOW_LIVE_HTTP=true`** の **二重ゲート**のみ |
| **Task 3 以降** | レスポンス正規化・キャッシュ・レート制限・トークン期限の自動更新 |

### Task 2 で追加したこと（要約）

- **`safe_auth_status()`**: プレゼンスフラグと `token_preview: "***"` のみ（**トークン実値・パスワード・raw を出さない**）。
- **`JQuantsClient`**: 公開戻り値に **refresh / id 実値・raw JSON を含めない**。ライブチェーンで得た機密は **メモリ内のみ**。
- **`debug jquants-status`**: **プローブ無し**。標準出力に秘密を載せない。
- **`debug jquants-daily-quotes`**: 既定 **dry-run**。`**--live` + `JQUANTS_ALLOW_LIVE_HTTP=true`** のときのみ実 HTTP を試行。
- **`make verify` / `daily` / `pack` / `risks`**: **変更なしで J-Quants へ接続しない**。CI と同様。

### ライブ HTTP の前提（Codex / 安全運用）

- **`JQUANTS_ENABLED=true`** は必要だが **それ単体では不十分**。**`--live`** と **`JQUANTS_ALLOW_LIVE_HTTP=true`** を **両方**満たすこと。
- 認証情報は **GitHub Secrets に置かず**、**ローカル `.env` のみ**（運用規約）。

### 認証フロー（公式想定）

- `POST /v1/token/auth_user` — mailaddress / password → refreshToken
- `POST /v1/token/auth_refresh` — refreshToken → idToken
- `GET /v1/prices/daily_quotes` 等 — `Authorization: Bearer <idToken>`

※ ベース URL は `JQUANTS_API_BASE_URL`（既定 `https://api.jquants.com/v1`）。パスは実装で `/token/...` のように **ベース直下**を結合。

## 認証情報を Git に載せない方針

- **実メール・パスワード・refresh / id トークン**は **`.env` にのみ**置く（**Git にコミットしない**）。
- **`.env.example` には変数名だけ**。**実値を書かない**。
- **`JQUANTS_ID_TOKEN` / `JQUANTS_REFRESH_TOKEN` は期限付き**。失効時は再取得または `auth_refresh`。運用では期限とローテーションをドキュメント化する。

## API キーなしでも stub で動く方針

- **`JQUANTS_ENABLED=false`**（既定）では `JQuantsStubAdapter` / `JQuantsClient` ともに **ネットワークに出ない**経路のみ。
- **GitHub Actions** でも **Secrets を使わず**、**実接続は行わない**。

## 将来取得したいデータ（J-Quants API）

- `listed/info`
- `prices/daily_quotes`
- `fins/statements`
- `fins/announcement`

## AI / 開発者向け注意

- **AI Agent にメール・パスワード・トークンを渡さない**（[07_ai_development_workflow.md](./07_ai_development_workflow.md)）。
- 実接続を試す場合は **ローカルのみ**、`JQUANTS_ENABLED=true` と **自分の `.env`** を人間が管理する。

## 次タスク（Task 3 候補）

- ID トークン期限検知・自動 refresh
- `listed/info` / `fins/*` のクライアントメソッドとテストモック強化

関連: [07_ai_development_workflow.md](./07_ai_development_workflow.md) · [06_phase0_completion_report.md](./06_phase0_completion_report.md)
