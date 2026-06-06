# v1.5 Price/Volume MVP Approval Request

## 目的

fixture-only分類から、read-only price/volume validationへ進むための承認依頼。

## 承認を求める範囲

- read-only price/volume fetch
- candidate/benchmarkの比較検証
- validation report作成

以下は承認対象外のまま維持する。

- cache write
- broker API
- trading / order placement
- actual import
- raw broker data
- secret / env値表示
- Gmail send
- workflow change

## Candidate Sources

- yfinanceまたは同等のpublic OHLCV source
- source reliability、rate limit、欠損、遅延を明示する
- corporate actions調整の完全性は検証完了まで保証しない

## Metrics

- Recent Return
- MA Deviation
- Volume Inflection
- RS Acceleration
- Theme-level average strength

## Validation Plan

1. v1.4 fixture classificationとv1.5 data-backed classificationを比較する。
2. Early Discovery / Theme Proxy / Do Not Chase / empty Early Discoveryを確認する。
3. missing dataとcorporate action疑義を明示する。
4. performance claimや自動投資行動へ接続しない。

## Stop Conditions

- missing data
- source instability
- suspicious corporate action adjustment
- secret / env exposureの兆候
- cache write、broker、trading、importが必要になる場合

## 承認文

`承認: v1.5 read-only price/volume MVP validationのみ YES / cache write・broker・trading・import・secret表示 NO`
