<!-- fixture-only / sanitized sample — not trading advice; no live data accuracy claim -->

# Portfolio Data Quality Review

- 対象月: 2026-05
- 判定: WARN
- source_mode: fixture_or_sanitized_manual_only
- Safety: これは売買指示ではなく、portfolio入力品質と配分上の注意を確認するレビューです。

## Review Items

| key | severity | category | review | next check |
| --- | --- | --- | --- | --- |
| invalid_amount_unit | INFO | unit | 金額単位: 整合確認済み: currency=JPY / amount_unit=man_yen 単位誤認は全ての資産額・純資産評価を壊します。 | 人間入力時にJPY / man_yen契約を再確認する。 |
| net_worth_mismatch | INFO | amount | 純資産整合: 整合確認済み: 総資産4327.9 - ローン3432.0 = 純資産895.9万円 純資産不整合は配分比率とリスク余力の前提を歪めます。 | 総資産・ローン残高・純資産の同一時点性を確認する。 |
| asset_total_mismatch | INFO | amount | 資産分類合計: 整合確認済み: 資産分類合計4327.9 / 総資産4327.9万円 分類漏れや二重計上はportfolio制約判定を誤らせます。 | 資産分類の漏れ・重複がないことを確認する。 |
| ratio_total_mismatch | INFO | ratio | 比率合計: 整合確認済み: 資産分類比率合計99.9% 比率合計の不整合は配分ギャップ評価を無効にします。 | 丸め差を除き100%へ整合することを確認する。 |
| equity_total_mismatch | INFO | equity | 株式系合計: 整合確認済み: INDEX2088.2 + 個別株846.3 = 株式系合計2934.5万円 株式系合計はportfolio risk制約の主要入力です。 | INDEXと個別株の分類境界を確認する。 |
| cash_below_minimum_guardrail | WARN | guardrail | 現金比率ガードレール: 現金11.7% / minimum 15.0% 現金不足は新規リスク追加余力を制限します。 | 最新入力でもminimum未満かを人間が確認する。 |
| single_stock_above_target_band | WARN | guardrail | 個別株比率ガードレール: 個別株19.6% / target max 15.0% 個別株比率超過は集中・高ボラリスクを増やします。 | 最新入力と分類定義で超過が継続しているか確認する。 |
| target_allocation_gap | WARN | ratio | 目標配分ギャップ: cash -18.3pt / equity +18.8pt / alternative -3.6pt / bond +3.0pt 目標配分との差は候補評価時のportfolio制約です。 | 目標比率と現在比率が同じ分類ルールか確認する。 |

## Manual Confirmation Items
- 対象月2026-05が最新portfolio inputか確認する。
- currency=JPY / amount_unit=man_yenが共有契約と一致するか確認する。
- 総資産・ローン残高・純資産・各資産分類が同一時点の値か確認する。
- raw Excel / broker exportを直接解析せず、redacted/sanitized入力であることを確認する。

## Explicit Non-Approval
- live HTTP / provider access: not executed / not approved
- cache write / actual import: not executed / not approved
- broker API / raw Excel direct parsing: not executed / not approved
- trading action / real email send: not executed / not approved
