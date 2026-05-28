# Cache Refresh Operator One-Pager

## 目的
- cache refresh 実行前に、対象・安全ゲート・手順・ロールバックを1ページで確認する。
- 本書は運用手順書であり、実refreshの自動実行を有効化しない。

## 前提
- observation-only を維持する。
- 実行対象は execution plan で明示された ticker のみ。
- default は dry-run。
- live HTTP / cache write / actual refresh は明示ゲートが揃うまで禁止。

## 必須ゲート
- `ALLOW_LIVE_HTTP=1`
- `CONFIRM_LIVE_HTTP=YES`
- `ALLOW_CACHE_WRITE=1`
- `CONFIRM_CACHE_WRITE=YES`
- `CONFIRM_CACHE_REFRESH=YES`

## 実行禁止事項
- 実refreshの無差別実行
- 対象外tickerの更新
- source repo への生成物 commit
- secrets/token の表示
- workflow 変更やスケジュール実行

## 推奨順序
1. readiness / execution plan / execute dry-run / jp dry-run を再生成
2. 対象限定の判断（JP先行か、US同時か）を人間が決定
3. 別PRで gate 付き実refresh実装をレビュー
4. postcheck を実行して before/after 差分を確認
5. reports-private 同期と ChatGPT upload セット更新

## 失敗時ロールバック
- refresh 実行を中断し dry-run のみ再実行
- before/after JSON を保全し postcheck で差分を記録
- 影響対象tickerを縮小し、次PRで再試行

## postcheck チェック項目
- `freshness_classification` の変化
- `stale_days` の減少
- readiness 対象の減少
- execution plan 対象の減少
- trap analysis の鮮度リスク記述の変化

## reports / upload
- reports-private `latest` と `weekly/YYYY/YYYY-MM-DD` を同期
- upload ディレクトリへ以下を配置
  - `chatgpt_invest_context_pack.md`
  - `trap_analysis.md`
  - `validation_dashboard.md`
  - `cache_refresh_readiness.md`
  - `cache_refresh_execution_plan.md`
  - `cache_refresh_execute_dry_run.md`
  - `jp_cache_refresh_dry_run.md`
  - `cache_refresh_postcheck.md`
