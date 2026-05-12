# Phase 1a — J-Quants 接続計画

## Phase 1a の目的

- 日本株ウォッチリストを **テーマ付きで整理**し、将来のシグナル・日次レポートに載せられる形にする。
- **シグナル検知への再フォーカス**：アルファニュメリックなど **JP コードの種類ごとの観察**（例：**`285A` / Kioxia 型に代表される銘柄**）が **skipped だけで無視されない**こと。
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
| **Task 2** | `JQuantsClient`（認証・`daily_quotes` の内部 HTTP 骨格）。**`debug jquants-status` は HTTP 禁止**。ライブ経路は **環境＋CLI のゲート**で制御（**Task 4** で **`JQUANTS_ENABLED`・BASE URL・（V2）`JQUANTS_API_KEY` まで必須化**） |
| **Task 3** | **ローカル手動接続ガイド**（[09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md)）、`config/market_data.yaml` の jquants メタ、`JQUANTS_API_VERSION` / `JQUANTS_API_BASE_URL` 対応、`safe_auth_status` 拡張。**このタスクでは実 API 接続や正規レスポンス処理は行わない** |
| **Task 3.1** | **安全強化**: `JQUANTS_API_VERSION` を **`v1` / `v2` のみ許可**（それ以外は `unsupported_version`・**実 HTTP なし**）。**`JQUANTS_API_BASE_URL` 未設定時はライブ許可があっても `not_configured`（`base_url_missing`）**。CLI / テストで回帰を防ぐ |
| **Task 4** | **Version2 プライマリ寄せ**: **`JQUANTS_API_KEY`** と **`x-api-key`**、V2 パス（`/equities/bars/daily` 等）を `JQuantsClient`・設定・ドキュメントへ反映。V1 は **legacy** のまま **`JQUANTS_API_VERSION=v1` のみ**。**本タスクでは実 API 呼び出しは行わない**（テストは mock のみ） |
| **Task 4.1** | **`debug jquants-daily-quotes --live` の exit を厳格化**: 実 HTTP に至らなかった live 試行は **非ゼロ終了**。`live_blocked` / `not_configured` / `unsupported_version` / `disabled`（live 時）などを **成功と誤認しない**。**`--live` なしの dry-run と `make verify` は従来どおり exit 0** |
| **Task 4.2** | **V2 ライブ応答の検証**: HTTP 200 のみでは **`success` にしない**。非 JSON・不正トップレベル型は **`non_json_response` / `invalid_response`**（一覧キーの中身までの厳密化は **Task 5**） |
| **Task 5** | **ローカル最小 live smoke の準備**（運用・手順は **[09](./09_jquants_local_manual_test.md)**）。**実 API Key は人間のみ**。`normalize_v2_daily_bars_response` により、`data` / `daily_quotes` / `bars` / `results` のうち **先に見つかったキーの値が list** のときのみ `success` と **`row_count` / `source_key`** を返す（空 list は `success`・`row_count=0`）。**GitHub Actions では live に接続しない** |
| **Task 5.1** | **V2 daily bars のクエリキーを公式に整合**：`from` / `to` / `date`（**非 `from_date` / `to_date`**）。日付の **HTTP 送信値は Task 5.4 で `YYYYMMDD` に統一**（以前の **YYYY-MM-DD 送信**は廃止）。`http_error` は **`http_status`** と安全フィールドのみ（raw body なし） |
| **Task 5.2** | **安全デバッグ**：`build_v2_daily_bars_request_preview()` と **`debug jquants-daily-quotes --preview-request`**（**実 HTTP を一切しない**）。`http_error` で **`endpoint_url_without_query` / `query_params` / `full_url_without_secrets`** と **`api_key_header_present`（値は不出力）**。BASE が `/v2` でもパス側の重複 **`/v2/v2`** を避ける結合ユーティリティ |
| **Task 5.3** | **コード／日付の柔軟な切り分け**：`debug jquants-daily-quotes` で **`code`のみ / `date`のみ / `code`+`date` / `code`+`from`〜`to`** を HTTP 前に検証したうえで試せる。**`--date`** と **`--from-date`/`--to-date`** は排他。**公式クエリは `code` / `date` / `from` / `to` のみ**（`from_date` 等は送らない）。**live smoke ではまず `--preview-request` と code-only/date-only で 400 を切り分ける** |
| **Task 5.4** | **V2 日付クエリを `YYYYMMDD` で送信**（公式クイックスタートの例に合わせる）。CLI は **`YYYY-MM-DD`** または **`YYYYMMDD`** を入力可。**`query_params` と `preview-request` は実送信値**（ハイフンなし 8 桁）。無効な日付は **`invalid_date_format`** |
| **Task 5.5** | **HTTP エラー時の安全プレビュー**：`http_error` に **短いマスク済み `error_body_preview`**（最大約 300 文字、**raw body は返さない**）。`JQUANTS_API_KEY` 等は伏字 |
| **Task 5.6** | **データ提供範囲ガード**：**`JQUANTS_DATA_AVAILABLE_FROM` / `TO`**（両方とも人間が `.env` で設定）が **解釈可能なときだけ**、**`--date` / `--from-date` / `--to-date`** が **契約ウィンドウ外**なら **HTTP 前に `validation_error` / `date_out_of_available_range`**（`config/market_data.yaml` に env 名メタあり） |
| **Task 6** | **`debug jquants-watchlist-bars`**：**`jp_watchlist`** を順に **`get_daily_quotes` / preview**。**既定 dry-run**、**`--preview-request`** は HTTP なし、**live は三重ゲート + Task 5.6**。**コード分類（wire）**：**ASCII 英数字ちょうど 4 文字**（**大文字へ正規化**。例：**`7011`・`285A`**）；**それ以外は `skipped_unsupported_code`**（**Phase 1a Re-focus Task 1** でミックス銘柄を許可）。**単体 `jquants-daily-quotes` は厳しい 4 字制約にしない**。 |
| **Task 7** | **`alpha-os daily`** に **J-Quants Watchlist Bars Check**（**dry_run / 集計のみ、HTTP なし**）。`config/market_data.yaml` の **`adapters.jquants.report`**。**API Key・raw・`x-api-key` 値は出さない**。**CI / `make verify` でも live しない** |
| **Task 8** | **`alpha-os daily`** に **readiness（Green / Yellow / Red）** と **skipped コード一覧**。**HTTP なし**・設定は **`adapters.jquants.report`**（`readiness_*`）。**実 API は呼ばず**環境ガード可否・ウォッチリスト集計のみ |
| **Task 9** | **`debug jquants-watchlist-bars --save-summary`**：**sanitized** な要約 JSON を **`outputs/jquants_smoke/`** に保存（**raw・API Key・`x-api-key`・ヘッダー全体は保存禁止**）。**`--preview-request` では保存しない**。**dry-run / live 完了**の両方で保存可。**`daily` / CI / `make verify` は変更なしで live しない** |
| **Task 9.1** | **Smoke summary カウンタ**：**`dry_run`** を **`error_count` に含めない**。**保存 JSON** に **`dry_run_count`** / **`preview_count`** を追加。ライブ完了時、CLI 出力は **`completed`** でも **保存 `mode` は `live`**（Task 10 の daily 取り込み前提） |
| **Task 9.2** | **契約データ範囲の実反映**と **watchlist limit 3 live smoke 成功のドキュメント化**：[09](./09_jquants_local_manual_test.md)・**`.env.example`** の **`JQUANTS_DATA_AVAILABLE_*` 例**を **実契約（例：`2024-02-17`〜`2026-02-17`）と整合**。**記録済み**：`7011` / `6501` / `6506`、`date=2024-02-19`、`--save-summary`。**`outputs/jquants_smoke/*.json`** は Git 対象外のまま |
| **Task 10** | **`alpha-os daily`** が **`outputs/jquants_smoke/latest.json`**（**ローカルにだけある sanitized**）を **読んで本文に「Latest local smoke summary」を出す**。**ファイル読み取りのみ**。**`daily` / `make verify` / CI は live HTTP しない**（**`include_latest_smoke_summary`**、`latest_smoke_summary_*` は `config/market_data.adapters.jquants.report`） |
| **Task 11** | 必要なら **readiness を `latest.json` の内容で Green+ / Yellow に細分化**（**自動 live は禁止のまま**） |

### DevOps — ローカル運用ショートカット（Task / 並行項目）

- **Makefile**：**`make env-doctor`** / **`make daily-check`** / **`make jquants-smoke-dry-run`**（`DATE`,`LIMIT`。**live しない**・**`--save-summary`**）/ **`make jquants-smoke-live`**（**`CONFIRM_LIVE_HTTP=YES` ゲート**。子プロセスだけ **`JQUANTS_ALLOW_LIVE_HTTP=true`** と **`--live --save-summary`**）/ **`make post-push-check`**（`gh` があれば最新 Actions メタのみ）/ **`make ops-check`**（上記の **`env-doctor` → `daily-check` → `post-push-check`** で **live HTTP なし**）。
- **`scripts/`**：`scripts/env_doctor.sh` など実装。**API Key は表示しない**。外部レビュー用のひとつの全体資料は **`docs/10_system_overview_for_external_review.md`**。

### Phase 1a Re-focus — Task 1（アルファニュメリック東証コード / 285A）（完了）

外部レビューで **`285A`**（キオクシア型・東証アルファニュメリック柄）が **`skipped_unsupported_code`** と解釈され得た点を **Corrective** とし、**シグナル検知への再フォーカス**の一環として対応済みとする。

- **`jquants_daily_bars_ticker_kind` / `normalize_jquants_equity_code`**：watchlist での J-Quants daily bars は **ASCII `[A-Za-z0-9]` ちょうど 4 文字**を **`ok`**（送信用は **`upper()` 正規化**）。記号・全角・5 文字超・空などは **`skipped_unsupported_code`**。**単体の `debug jquants-daily-quotes`** はこれまでどおりコード形式を厳しすぎる制約にしない（**5 桁等の公式コード**の探索用）。
- **`debug jquants-watchlist-bars`** の **`--preview-request` / dry-run**：**`285A`** が **`query_params.code: \"285A\"`**（**`date` は `YYYYMMDD` wire**）で出る。

### Phase 1a Task 2（JQuants クライアント骨格）で追加したこと（要約）

- **`safe_auth_status()`**: プレゼンスフラグと `token_preview: "***"` のみ（**トークン実値・パスワード・raw を出さない**）。
- **`JQuantsClient`**: 公開戻り値に **refresh / id 実値・raw JSON を含めない**。ライブチェーンで得た機密は **メモリ内のみ**。
- **`debug jquants-status`**: **プローブ無し**。標準出力に秘密を載せない。
- **`debug jquants-daily-quotes`**: 既定 **dry-run**。V2 ライブ実 HTTP は **`JQUANTS_ENABLED` + `--live` + `JQUANTS_ALLOW_LIVE_HTTP=true` + BASE URL + `JQUANTS_API_KEY`** が揃ったときのみ。
- **`make verify` / `daily` / `pack` / `risks`**: **変更なしで J-Quants へ接続しない**。CI と同様。

### Task 3 で追加したこと（要約）

- **[09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md)** — 人間向けローカル手動確認、三重ゲート（+ BASE URL・V2 では API Key）、トラブルシュート。
- **`JQUANTS_API_BASE_URL` 未設定時**はネットワークを伴う処理を **`not_configured`**（**`reason: base_url_missing`**）で止める（フォールバック固定 URL なし）。**`JQUANTS_ALLOW_LIVE_HTTP=true` かつ `--live` が付いていても同様**。
- **`safe_auth_status()`** に **`api_version` / `api_version_effective` / `unsupported_api_version` / `base_url_present` / `allow_live_http`** を明示。
- **`config/market_data.yaml`** に `api_version`、`base_url_env`、`ci_live_http: disabled`、`manual_live_http: triple_gate_required` 等。

### Task 3.1 で追加したこと（安全強化）

- **`JQUANTS_API_VERSION` 厳格化**: 許可は **`v1` / `v2`（および定義済みエイリアス）のみ**。それ以外は **`unsupported_version`** 応答とし、**urllib による実 HTTP を実行しない**。
- **`debug jquants-status`**: `unsupported_api_version` / `api_version_effective` を表示（**秘密は出さない**）。
- **テスト**: `base_url` 未設定かつ **full live 意図**でも `urlopen` が呼ばれないこと、未知 version でも HTTP しないことを明示。

### Task 4.1 で追加したこと（exit code）

- **`debug jquants-daily-quotes`**: **`--live` あり**かつ実 HTTP が行われなかった場合（`live_blocked`、`not_configured`、`unsupported_version`、live 時の `disabled`、`failed` / `http_error` / `error` など）は **exit 1**。**`success` のときのみ exit 0**。`--live` なしと `make verify` の挙動は維持。

### Task 4.2 で追加したこと（live response validation）

- **V2 `get_daily_quotes` ライブ**: HTTP ボディが **JSON オブジェクト／配列など**になり得た段階のゲート。**Task 5** で **`normalize_v2_daily_bars_response`** に一覧キーごとの **list 必須**を寄せ、`success` 時は **`row_count`** と **`source_key`** で要約。**raw は戻り値にも CLI にも載せない**。

### Task 5 で追加したこと（live smoke 準備・正規化の初期版）

- **`normalize_v2_daily_bars_response(payload: dict)`**（**API Key／token／raw を返さない**）。探索順は **`data` → `daily_quotes` → `bars` → `results`**。**最初に現れたキーの値が list でなければ `invalid_response`**。いずれのキーも無ければ `missing_list_field`。**空 list は `success`・`row_count=0`**。
- **`debug jquants-daily-quotes`**：`--live` なし → dry-run で **exit 0**；成功時出力は **`status` / `row_count` / `source_key` / `code` / 日付**程度。**秘密と raw は出さない**。
- **実 API Key と実 live 確認は人間のみ**（[09](./09_jquants_local_manual_test.md)）。CI は **変更なしで live に出ない**。

### Task 5.1 で追加したこと（V2 daily bars クエリ整合）

- **`GET …/equities/bars/daily`** のクエリは公式名 **`code` / `date` / `from` / `to`** のみ。**`from_date` / `to_date` を送らない**。
- **`--from-date` / `--to-date`**（CLI）は **`from` / `to`** に変換し、**API 送信値は Task 5.4 とおり `YYYYMMDD`**（CLI は `YYYY-MM-DD` も可。詳細は [09](./09_jquants_local_manual_test.md)）。**ライブでの HTTP 400** はクエリ・日付形式・コード形式を優先確認（[09](./09_jquants_local_manual_test.md)）。
- **`http_error` 応答**は **`http_status`** と安全フィールドのみ（**raw body なし**）。

### Task 5.2 で追加したこと（安全リクエストプレビュー・HTTP エラー強化）

- **`build_v2_daily_bars_request_preview`** と **`alpha-os debug jquants-daily-quotes --preview-request`**：**実 HTTP は行わない**（`JQUANTS_ALLOW_LIVE_HTTP=true` でも **preview のみでは urlopen しない**）。出力は **`query_params`**・パス **`/equities/bars/daily`** と結合済み **`full_url_without_secrets`**。**API Key の実値・ヘッダー全体・raw body は出さない**（`api_key_value_included: false`）。
- **`http_error`（例: 400）**に **`endpoint_url_without_query` / `query_params` / `full_url_without_secrets` / `api_key_header_*` メタのみ** を付加（応答ボディは出さない）。
- **`_join_v2_base_and_path`**：ベース URL が **`.../v2`** でパスが誤って **`/v2/equities/...`** でも **`/v2/v2`** にならないよう正規化。

### Task 5.3 で追加したこと（CLI 切り分け・クエリ妥当性）

- **`debug jquants-daily-quotes`**：`--code` / **`--date`（新規）** / **`--from-date`** / **`--to-date`** をすべて任意に。**いずれも無い場合**や **`--date` と `--from-date`/`--to-date` の併用**は **`validation_error`**（実 HTTP／プレビュー JSON に進む前）。**`--preview-request`** も同じ検証を通す。**V2 で送るクエリキーは `code`・`date`・`from`・`to` のみ**。**応答側の公式前提と別に、`from`/`to` の片方のみ**による試行も CLI として許す（サーバが 400 を返す切り分け用）。
- **運用**：**live smoke では、`--preview-request` のあと `--code` のみ、`--date` のみから試し**、`from`〜`to` レンジは切り分けが進んでから。**レンジは `from` と `to` の両方揃えることを推奨**（CLI は片方だけも許容）。

### Task 5.4 で追加したこと（公式どおりの日付 wire **`YYYYMMDD`**)

- **`_parse_v2_daily_bars_date`**: CLI 入力は **`YYYY-MM-DD`（月日ゼロ埋め）** または **`YYYYMMDD`**。カレンダー無効 → **`validation_error` / `invalid_date_format`**。
- **V2 の `date` / `from` / `to` クエリ値**および **`--preview-request` の `query_params`・`full_url_without_secrets`** は、常に **8 桁 `YYYYMMDD`**（公式クイックスタートの `date="20240104"` 形式に整合）。
- **Task 5.1** で記載していた **ハイフン付きをそのままクエリに載せる**挙動は **本タスクで置き換え**。

### Task 5.6 で追加したこと（データ提供範囲 CLI ガード）

- **環境変数** **`JQUANTS_DATA_AVAILABLE_FROM`** / **`JQUANTS_DATA_AVAILABLE_TO`**（**`YYYY-MM-DD` または `YYYYMMDD`**）を **両方**満たすと解釈できるときだけ、V2 の **`validate_daily_quotes_cli_args`** が **各指定日**を **両端込みの契約ウィンドウ**と照合する。**未設定・片方だけ・解釈不能・`from > to`** のときは **`make verify` 互換のためガード無効**（従来どおり）。
- 範囲外は **`validation_error` / `date_out_of_available_range`**。応答に **`data_available_from`** / **`data_available_to`**（ISO **日付のみ**）と CLI 側の **`date` / `date_from` / `date_to`**。**API Key / raw は含めない**。**`--preview-request` と dry-run でも** HTTP 前に同じ検証が走る。**`code` のみ**（日付なし）では照合しない。

### Task 6 で追加したこと（watchlist・daily bars 一括確認）

- **`invis_alpha_os.config.jp_watchlist`**：`jp_watchlist` を抽出。**Phase 1a Re-focus Task 1**：**`normalize_jquants_equity_code` / `jquants_daily_bars_ticker_kind`** — **ASCII 英数字ちょうど 4 文字**を **`ok`**（wire は **大文字**）。**記号・全角・長さ≠4**は **`skipped_unsupported_code`**（例：**`285A`・`304A`・`7011`** は **wire 対象**）。
- **`alpha-os debug jquants-watchlist-bars`**：**`--date`** または **`--from-date`/`--to-date`（レンジは両方必須）** 。**`--limit`**・**`--preview-request`**・**`--live`**。トップレベル **`raw_response_included: false`**。

### Task 8 で追加したこと（daily readiness・HTTP なし）

- **`render_jquants_watchlist_bars_check_section`**：先頭に **`Readiness`**（緑／黄／赤）。**skipped コード**一覧（URL や全銘柄 URL は出さない）。**`live_http_in_daily` は常に `disabled` を要求**（違反時は Red）。
- **Green（例）**：supported > 0、（設定どおり）**データ範囲ガード両系有効**、（設定どおり）**smoke 記録オン**、raw/API 表示オフ、ウォッチリスト読込成功。**ウォッチリストに wire 対象外のティッカーが残るときだけ**、その数が **`Unsupported code count`** に反映される（**Re-focus のあとでも、例：将来の異常行や手入力ならび外し**）。
- **Yellow**：Red 条件でなく、Green の厳密条件の一部が欠ける（例：ガード未設定で `readiness_green_requires_data_guard: true`）。
- **Red**：supported 0、ウォッチリスト読込失敗、raw/API 表示オン、**`live_http_in_daily` ≠ disabled** など。
- **Smoke 状態行**：レポートは **`daily` 中に live smoke を実行しない**ため、**運用合格の `passed` は使わず**、**参照用サブセクションの有無を `documented reference` 等で示す**。

### Task 9 で追加したこと（ローカル sanitized smoke ファイル・HTTP は人間の live のみ）

- **`--save-summary`**：`reporting/jquants_smoke_summary.py` 経由で **`outputs/jquants_smoke/watchlist_bars_<slug>_limit<N|all>.json`** と **`latest.json`** を出力。保存内容は **`code` / `status` / `row_count` / `source_key` / `http_status` / `error_body_preview`** 等に限定し、**クエリ・URL・Key・raw body は書かない**。
- **Task 9.1**：集計は **`success_count` / `error_count`（異常系 `status` のみ） / `skipped_count` / `dry_run_count` / `preview_count`**。ライブ後の CLI トップ **`status`** が **`completed`** でも、保存 JSON の **`mode`** は **`live`**。
- **Task 9.2**：実契約のデータ適用ウィンドウ（**.env は各ユーザー**。リポでは **`.env.example` のみ例示：2024-02-17〜2026-02-17**）と、[09](./09_jquants_local_manual_test.md) への **watchlist limit 3 live + `--save-summary` 成功の記録**。**smoke の `*.json` は Git にコミットしない**。
- **Task 10**：**`daily`** が **`outputs/jquants_smoke/latest.json`** を **読むだけ**で **「Latest local smoke summary」**を本文に追加（**unsafe なキーや `raw_response_included` / `api_key_displayed` が true のときは blocked 表示**）。**`urllib` / live HTTP なし**。**`include_latest_smoke_summary`** 等は **`adapters.jquants.report`**。
- **`alpha-os daily`** は引き続き **live しない**。

- **Version2 は API Key 方式**（HTTP ヘッダー **`x-api-key`**）。**refreshToken / idToken 方式は V2 プライマリでは使わない**。
- **`JQUANTS_API_VERSION=v2`（既定）**のとき、`get_refresh_token` / `get_id_token` は **`not_applicable`**（legacy は `v1` へ切替）。
- **`JQUANTS_EMAIL` / `JQUANTS_PASSWORD` / `JQUANTS_REFRESH_TOKEN` / `JQUANTS_ID_TOKEN` は V1 legacy** 用として `.env.example` に残すのみ（V2 運用の主軸ではない）。

### Task 4 で追加したこと（V2 設計寄せ）

- **`_paths_for_version("v2")`** を公式例に沿った相対パスへ更新（`/equities/master`、`/equities/bars/daily` 等）。
- **実 HTTP（`debug jquants-daily-quotes --live`）** の前提を **三重条件＋設定**に拡張:**`JQUANTS_ENABLED` + `--live` + `JQUANTS_ALLOW_LIVE_HTTP` + `BASE URL` + `JQUANTS_API_KEY`**（詳細は [09](./09_jquants_local_manual_test.md)）。
- **API Key 実値・トークン実値は CLI 出力に含めない**（`api_key_preview` / `token_preview` は `***` のみ）。

### ライブ HTTP の前提（Codex / 安全運用）

- **`JQUANTS_ENABLED=true`** は必要だが **それ単体では不十分**。**`--live`** と **`JQUANTS_ALLOW_LIVE_HTTP=true`** を **両方**満たすこと。
- **V2 では** さらに **`JQUANTS_API_BASE_URL`**（非空）と **`JQUANTS_API_KEY`**（非空）が必要。欠落時は **`not_configured`**（`base_url_missing` / `api_key_missing`）。
- **`JQUANTS_API_VERSION` が `v1` / `v2` に解決できる**こと（Task 3.1）。
- **V1 legacy** の Bearer 実 HTTP は **`JQUANTS_API_VERSION=v1`** のときのみ `get_daily_quotes` のライブ分支で利用可能。
- 認証情報・API Key は **GitHub Secrets に置かず**、**ローカル `.env` のみ**（運用規約）。

### 認証・エンドポイント

- **V2（primary）**: `GET` 等で **`x-api-key: <JQUANTS_API_KEY>`**。代表パス例は `config/market_data.yaml` の **`planned_v2_endpoints`** と `JQuantsClient._paths_for_version("v2")` を参照。
- **V1（legacy）**: refresh / id と **`Authorization: Bearer`**。**閉鎖予定**であり新規運用では非推奨。

## 認証情報を Git に載せない方針

- **API Key・実メール・パスワード・refresh / id トークン**は **`.env` にのみ**置く（**Git にコミットしない**）。
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

- **AI Agent に API Key・メール・パスワード・トークンを渡さない**（[07_ai_development_workflow.md](./07_ai_development_workflow.md)）。
- 実接続を試す場合は **[09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md)** に従い、**ローカルのみ**で人間が実施する。

---

関連: [09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md) · [07_ai_development_workflow.md](./07_ai_development_workflow.md) · [06_phase0_completion_report.md](./06_phase0_completion_report.md)
