> このサンプルは source-only / fixture-only の出力例です。
> 実データの正確性・鮮度を保証せず、売買指示ではありません。
> actual import / cache write / broker API / raw Excel parsing は実行していません。

# Raw Input Quarantine Review

## Quarantine Summary
- state: accepted_fixture
- source: fixture
- Import Readiness: NO-GO
- Cache Write Readiness: NO-GO

## Source Classification
- unit: man_yen
- currency: JPY
- statement_month: 2026-05
- redaction_status: redacted

## Hard Gate Status
- none declared

## Manual Confirmations Required
- none

## Data Quality Warnings
- none

## Next Actions
- manifest宣言とmanual confirmationを人間が確認する。
- raw payloadを読まず、sanitized/redacted summaryのみでreviewを継続する。
- actual import / cache writeは別承認までNO-GOを維持する。

## Safety Summary
- このquarantine reviewはsource-onlyであり、raw input読取・actual import・cache writeを実行しません。
- broker API / raw Excel direct parsing: not executed / not approved
- actual import / cache write: not executed / not approved
- trading action / real email send: not executed / not approved
