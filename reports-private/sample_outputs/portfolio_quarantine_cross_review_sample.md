> このサンプルは source-only / fixture-only の出力例です。
> 実データの正確性・鮮度を保証せず、売買指示ではありません。
> actual import / cache write / broker API / raw Excel parsing は実行していません。

# Portfolio / Raw Input Quarantine Cross-Review

## Cross-Review Summary
- state: manual_review_required
- portfolio quality: WARN
- quarantine: accepted_fixture
- source: fixture
- Import Readiness: NO-GO
- Cache Write Readiness: NO-GO

## Common Validation Taxonomy Mapping
- asset_total_mismatch
- cash_below_minimum_guardrail
- equity_total_mismatch
- invalid_amount_unit
- net_worth_mismatch
- ratio_total_mismatch
- single_stock_above_target_band

## Manual Confirmations Required
- 対象月2026-05が最新portfolio inputか確認する。
- currency=JPY / amount_unit=man_yenが共有契約と一致するか確認する。
- 総資産・ローン残高・純資産・各資産分類が同一時点の値か確認する。
- raw Excel / broker exportを直接解析せず、redacted/sanitized入力であることを確認する。

## Next Actions
- portfolio data quality warningとquarantine宣言を人間が横断確認する。
- raw payloadを読まず、sanitized/redacted declarationのみを維持する。
- actual import / cache writeは別承認までNO-GOを維持する。

## Safety Summary
- cross-reviewはsource-only skeletonであり、raw parsing・actual import・cache writeを実行しません。
- broker API / raw Excel direct parsing: not executed / not approved
- actual import / cache write: not executed / not approved
- trading action / real email send: not executed / not approved
