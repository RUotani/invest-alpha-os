# v106 Common Validation Taxonomy Assessment

## 3行サマリー

- v95/v97/v98/v100の実ファイルから40 keyを棚卸しし、validator issueとreview itemを分離した。
- 明確な命名揺れは2組、同一normalized meaning内のseverity揺れは0組だった。
- v98をcanonical input候補とし、非破壊の薄いtaxonomy skeletonは有益と判断する。

## 結論

v107でseverity/category/canonical key/legacy alias mappingだけを追加する価値がある。既存validatorへの接続、
issue key変更、severity変更、validation順序変更は行わない。

## Inventory Summary

| source | role | key count | assessment |
| --- | --- | ---: | --- |
| v95 | downstream monthly validator | 12 | v97/v98と重複する整合性・guardrail validationを持つ |
| v97 | projection/context validator | 9 | v95/v98と重複し、date/currency/negative amountは扱わない |
| v98 | sanitized/manual canonical input candidate | 14 | upstream schema/date/unit検証を含み、canonical候補として最も広い |
| v100 | user-facing reviewer | 5 | validator issueではなくreview projection。taxonomy issueと混ぜない |

## Duplicate Meanings

- v95/v97/v98共通: `net_worth_mismatch`, `asset_total_mismatch`, `equity_total_mismatch`,
  `cash_below_minimum_guardrail`, `single_stock_above_target_band`
- v95/v97共通: `cash_below_preferred_recovery_zone`
- v95/v98共通: `missing_as_of_month`, `future_as_of_month`, `negative_amount`
- v97/v98共通: `missing_required_asset_class`

## Naming Drift

| normalized meaning | current keys | recommendation |
| --- | --- | --- |
| invalid amount unit | `amount_unit_contract`, `invalid_amount_unit` | canonical keyは`invalid_amount_unit`、旧keyはaliasとして記録 |
| ratio total mismatch | `allocation_ratio_total_mismatch`, `ratio_total_mismatch` | canonical keyは`ratio_total_mismatch`、旧keyはaliasとして記録 |

## Severity Drift

同一normalized meaningのvalidator issue間でseverity揺れは検出されなかった。v100の`WARN|INFO`等は入力値に応じた
review severityであり、validator issue severityとは別契約として維持する。

## Canonical Source Candidate

`v98 sanitized/manual input -> v97 projection/context -> v95 downstream validator -> v100 reviewer`を推奨する。
ただしv98 canonical化は今回の挙動変更を意味せず、責務評価上の候補に留める。

## Commonize / Do Not Commonize

共通化候補:

- severity vocabulary
- issue category
- canonical key
- legacy alias mapping

まだ共通化しない:

- validation実行順序・条件・閾値
- domain-specific issue construction
- rendering文言・user-facing next action
- v100 review item key

## Safety / No-Go

- actual import / broker API / raw Excel parsing / live HTTP / cache write: NO-GO
- workflow / dependency / pyproject / Makefile変更: NO-GO
- trading action / real email send: NO-GO
