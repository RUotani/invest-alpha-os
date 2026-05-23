# peer_sync weekly opt-in

日付: 2026-05-24  
ステータス: approved  
関連ファイル: `docs/decisions/2026-05-24_peer_sync_cache_only_mvp.md`, `docs/150_product_observation_log_weekly_runbook.md`

## 結論(1〜3行)

- `weekly-us-observation --with-peer-sync` を opt-in で追加（default off）。
- peer_sync 本体ロジックは再利用; observation_log への peer 行 append は別 PR。

## 確度

- 90%

## 背景

- #216 で peer_sync MVP が main に入ったが weekly cycle 未統合だった。
- STATE §7 の follow-up PR 項目。

## 採用した選択肢の根拠

- daily/signals default を変えない opt-in フラグ
- 既存 `build_peer_sync_cache_only_report` の再利用

## 次のアクション

- [x] `--with-peer-sync` + markdown section + tests
- [ ] observation_log peer_sync note（別 PR）
