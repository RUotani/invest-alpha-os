# STATE.md Update Proposal — Post #510 / v1.6 Trial Send

作成日: 2026-06-06  
目的: STATE.md 直接更新はユーザー承認待ちのため、承認後に反映する差分案。

## 提案する §1 追記

- PR #508: v1.4 Early Discovery Pivot
- PR #509: v1.5 fixture-only early discovery metrics prep
- PR #510: v1.6 Weekly Report Trust & Mobile UI Repair
- latest verified main: `5c84ea7`（#510 merge）

## 提案する §2 Weekly 更新

### v1.6 trust · mobile UI（#510）

- 鮮度ゲート: fresh ≤14d / stale_warning 15–30d / expired >30d
- 過熱振り分け: `REPORT_UI_OVERHEAT_R20=0.50` · 初動0件週は過熱で埋めない
- 集計整合: `WeeklyReportRenderModel` が件数と本文の単一ソース
- copy block v1.6 構成 · モバイル縦カード · RED/YELLOW 除去
- sample: `reports-private/sample_outputs/weekly_report_v1_6_sample.md`

### v1.6 trial send（2026-06-06）

- trial root: `reports-private/trial_send/weekly_v1_6_2026-06-06/`
- Gmail sent: `19e9b98cdda38b5d`（gmail_oauth · email_preview_html）
- v1.2 trial 継続: `19e9a953c07c3a4a`

## 提案する 3行サマリー差し替え

```markdown
- **週次主系統**: Weekly Candidate Brief v1.6 — trust · mobile UI · freshness gate
- **latest verified main**: `5c84ea7`（#510 merge）
- **v1.6 trial**: `reports-private/trial_send/weekly_v1_6_2026-06-06/README_FOR_USER.md`
```

## 承認後コマンド

ユーザー承認後、STATE.md を上記に合わせて更新しコミットする。
