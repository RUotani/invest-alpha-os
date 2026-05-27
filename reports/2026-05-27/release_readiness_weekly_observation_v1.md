# Release readiness — Weekly Observation Report v1

日付: 2026-05-27

## MERGE 判断材料

| 項目 | 状態 |
| --- | --- |
| 1コマンドで週次レポート | ✅ `weekly-observation-report-v1` |
| US signals | ✅ sample に Manifest / Quality / batch |
| peer_sync | ✅ Peer sync (cache-only) セクション |
| veto | ✅ Risk veto + batch veto count |
| repeat | ✅ repeat signal symbols + checklist |
| forward validation | ✅ Forward validation summary |
| portfolio observation | ✅ Portfolio observation + exposure |
| P10 gap | ✅ tier-1 / stale_skip |
| next human actions | ✅ Next human actions |
| P3 未成熟の明記 | ✅ immature_monitoring · matched_normal=1/10 |
| live/cache/Gmail | ✅ なし（read-only） |
| default behavior | ✅ 既存 weekly dry-run 変更なし |

## sample report

- パス: [sample_weekly_observation_report_v1.md](./sample_weekly_observation_report_v1.md)
- 判断質問: **毎週これを見たいか？ 今週の観測判断に使えるか？**

## P3 再定義（decision 参照）

- P3 live forward usable: **time-dependent monitoring gate**（短期開発 KPI から除外）
- current: `matched_normal=1/10`, need 9
- portfolio readiness: P0–P2 は独立評価（v1 完成判定に P3 usable 不要）

## Tests

- targeted v1: 5 passed — 詳細 [test_report_weekly_observation_v1.md](./test_report_weekly_observation_v1.md)
- full suite: 1157 passed, **4 failed**（jquants / us_provider / daily golden — v1 変更と無関係の既存失敗）

## 人間アクション（2択のみ）

```text
MERGE — sample が週次観測に足る → release PR を squash merge
STOP  — sample が使えない → 追加開発せず一時停止
```

## PR

- `product: finalize Weekly Observation Report v1`（1本のみ）
