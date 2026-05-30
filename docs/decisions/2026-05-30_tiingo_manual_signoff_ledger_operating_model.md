# Tiingo manual signoff ledger operating model

日付: 2026-05-30
ステータス: approved-by-task
関連: v52 Tiingo Current Docs Manual Recheck Pack, v49 US OHLCV Pilot Approval Bundle, `RULES.md` §1

## 結論

- v54 は Tiingo live-fetch-only pilot 前の human/operator signoff ledger であり、実行承認ではない。
- 全 signoff item は default `unreviewed` とし、manual signoff incomplete の間は live fetch を承認しない。
- cache write と actual import は live fetch signoff とは別の承認境界として残す。

## No-write discipline

| 項目 | v54 の扱い |
|---|---|
| Tiingo API call | 実行しない |
| provider live access | 実行しない |
| public OHLCV source live fetch | 実行しない |
| cache write | 実行しない |
| actual refresh/import | 実行しない |
| manual actual import | 実行しない |
| env/secret 表示 | 行わない |
| broker/manual raw data | 扱わない |
| workflow/dependency/pyproject 変更 | 行わない |
| trading action | 行わない |

## Operator signoff

- Operator は各 item に current docs evidence を記入し、status を `reviewed_pass` / `reviewed_fail` / `needs_escalation` / `not_applicable` に更新する。
- `unreviewed` が残る間は live fetch approval phrase を出さない。
- cache suitability、no-write discipline、verification criteria は cache write / actual import の将来承認も block する。

## 反証

- 台帳があるだけでは証跡確認は完了していない。
- default status を `unreviewed` に固定し、final verdict を `manual_signoff_incomplete_live_fetch_not_approved` として誤承認を避ける。

## 次アクション

- Human/operator が v54 ledger に証跡とsignoff statusを記入する。
- 全live-fetch blockerが `reviewed_pass` になった場合のみ、別タスクで live-fetch-only approval phrase を検討する。
- cache write / actual import は pilot 結果レビュー後まで分離する。
