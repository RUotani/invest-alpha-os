# Phase 1a — J-Quants 接続計画

## Phase 1a の目的

- 日本株ウォッチリストを **テーマ付きで整理**し、将来のシグナル・日次レポートに載せられる形にする。
- **J-Quants API** を日本株の **primary source 候補**として組み込むための **adapter・設定・環境変数の器**を用意する。
- **このタスク（Task 1）では実 API 接続・認証フローは行わない**。キーなしでも `make verify` が通る状態を維持する。

## J-Quants 接続の段階設計

| 段階 | 内容 |
|------|------|
| **Task 1（今回）** | `JQuantsStubAdapter`、`config/market_data.yaml` の `jp_equity`、`config/watchlist.yaml` 整備、`.env.example` のプレースホルダ、daily レポートの **Japan Signals** 枠（stub） |
| **Task 2（次）** | リフレッシュトークン取得・ID トークン更新・`Authorization` ヘッダー付与の **HTTP クライアント実装**（ローカル `.env` のみ、Git 非管理） |
| **Task 3 以降** | 取得データの正規化・キャッシュ・エラーハンドリング・レート制限 |

認証で想定する要素（**実装は次タスク以降**）:

- リフレッシュトークン
- ID トークン
- `Authorization` ヘッダー（ベアラ等）

## 認証情報を Git に載せない方針

- **メール・パスワード・リフレッシュトークン・ID トークン**は **コミット禁止**。
- `.env` は個人環境のみ。リポジトリには **`.env.example` に空キーのみ**置く。
- CI でも **Secrets を使わない**構成を維持し、stub のみでグリーンにする。

## API キーなしでも stub で動く方針

- 環境変数 `JQUANTS_ENABLED=false`（デフォルト相当）では **`JQuantsStubAdapter.is_enabled()` が false**。
- アダプタは **HTTP を発行せず**、`disabled / not configured` あるいは空の stub ペイロードを返す。
- アプリ本体・テスト・`make verify` は **認証情報なし**で完走する。

## 将来取得したいデータ（J-Quants API）

- `listed/info` — 銘柄属性・上場情報
- `prices/daily_quotes` — 日足
- `fins/statements` — 財務諸表
- `fins/announcement` — 適時開示等

※ エンドポイント名・パスは実装フェーズで公式仕様と照合する。

## 今回やらないこと

- J-Quants への **実接続・ログイン・トークン取得**
- **`curl` での生産 API 叩き**
- **自動売買・注文**

## 次タスクで実 API へ進む条件

- 「認証トークンの取得・更新・失効時の扱い」がドキュメント化されている。
- **ローカル `.env`**（Git 管理外）だけに実値が置かれる運用が合意されている。
- **単体テスト**で HTTP をモックし、キー無し CI が引き続き通る設計になっている。
- **Observation Only + No Auto Trading** が変わらないこと。

関連: [07_ai_development_workflow.md](./07_ai_development_workflow.md) · [06_phase0_completion_report.md](./06_phase0_completion_report.md)
