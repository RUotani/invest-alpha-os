# Manual Issue — Weekly Report Packs

ローカル CLI で生成した週次レポート（scheduled run 未発火時の代替）。

## 今日読むファイル（固定入口）

```text
reports-private/manual_issue/latest/README_FOR_USER.md
```

## ディレクトリ

| パス | 説明 |
| --- | --- |
| `latest/` | 常に最新週を指す入口（`pointer.json` + README） |
| `weekly_YYYYMMDD/` | 週次実体パック（copy / json / email preview 等） |

## 更新ルール

新しい manual issue を発行したら:

1. `weekly_YYYYMMDD/` に生成物を置く
2. `latest/pointer.json` の `report_date` / `week_dir` を更新
3. `latest/README_FOR_USER.md` の要約を更新
