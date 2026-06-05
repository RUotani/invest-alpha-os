# Report MVP 80% Readiness Review — 2026-06-06

## What is now usable

| 領域 | 状態 |
| --- | --- |
| Weekly copy-ready brief | fixture + golden snapshots + UX language contract |
| Monthly decision sheet | v84 + integration pack + language pass |
| Email preview | dry-run 設計、`gmail_send_attempted=false` |
| status.json | v104 schema + local verify CLI |
| Quality / Quarantine | v109–v111 CLI + samples |
| Operator guide | `docs/operator_user_guide.md` |
| User 1-page summary | `weekly-report-user-summary` CLI |

## What is not usable yet

- **Natural scheduled artifact** — 未観測（2026-06-06 07:30 JST 以降）
- **CI JSON artifact** — workflow upload 未承認
- **Actual portfolio import** — 意図的 NO-GO
- **Real email send** — 未接続

## User review checklist

1. `weekly-report-user-summary --format markdown`
2. `real_or_pending_weekly_report_review_20260606.md`
3. `sample_outputs_review_for_user.md`
4. 07:30 JST 以降の scheduled observation 結果

## Next UX changes

- schedule success 後の実レポート vs sample 差分メモ
- workflow JSON upload 承認後の artifact 検証

## Blockers

- scheduled run 未観測
- workflow 変更承認待ち
