# Decision — Scheduled Observation Report Contract (2026-06-06)

## 結論

`scheduled_run_observation_20260606.md` の必須セクションと安全文言を `tests/test_scheduled_observation_report_contract.py` で固定する。

## 必須セクション

- Observation Summary
- Classification
- Findings / Missing / Gaps
- Next Actions
- Safety Summary（workflow_dispatch 未実行・workflow 変更なし）

## Safety

- read-only observation docs のみ
- workflow 変更なし
