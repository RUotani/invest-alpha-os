# Weekly Report v1.2 Design Principles

## 3行サマリー

- Weekly Report v1.2 は、候補発見と投資行動を分けて読むための意思決定支援レポートです。
- 表・色・status は、候補の優先度、注意点、次アクションを短時間で把握するために使います。
- 個別候補より portfolio guardrail を優先し、売買指示・自動売買・注文には使いません。

## なぜ表を使うか

表は、候補同士を同じ観点で比較するために使う。

- Executive Summary: 今週の状態、基本方針、最大リスクを最初に固定する。
- Portfolio Guardrails: 現金、個別株、株式系合計の制約を先に確認する。
- Candidate Comparison: 候補の理由、反証、今週の扱いを横並びにする。
- Deep Dive Cards: 1銘柄ごとに、理由、反証、確認する数字、見送り条件を漏れなく確認する。
- If / Then Decision Rules: 条件が変わったときの判断を事前に決める。

## 色とstatusの意味

| Status | 色 | 意味 | 行動 |
|---|---|---|---|
| DEEP DIVE | Green | 深掘りする価値がある | 決算・需給・割高感・反証を確認する |
| WATCH | Yellow | 条件待ち・過熱注意 | 追いかけず、価格・材料・決算を待つ |
| VETO | Red | 強い注意サイン | 原則、新規リスク追加しない |
| NO ACTION | Gray | 情報のみ | データ不足や対象外として記録する |

色は判断を速くするための補助であり、売買指示ではない。

## Deep Dive / Watch / Veto の読み方

- Deep Dive: 候補として調べる価値はある。ただし、すぐ行動する意味ではない。
- Watch: 候補性はあるが、過熱、決算前、重複、現金不足などで待つ。
- Veto: 条件が変わるまで原則見送り。veto理由が消えたら再評価する。
- NO ACTION: データ不足または情報のみ。未評価を評価済みのように扱わない。

## 売買指示ではない理由

このレポートは Global Multi-Asset Candidate Discovery OS の候補発見出力であり、発注・自動売買・売買指示を行わない。

- 価格帯や発注数量は出さない。
- broker API、actual import、cache write、live market fetch はこのUX改善の対象外。
- 候補は「調査する順番」であり、「今すぐ新規追加する対象」ではない。

## Portfolio Guardrail が個別候補を上書きする

個別候補が魅力的でも、現金比率や個別株比率の制約を優先する。

| Guardrail | 判断 |
|---|---|
| 現金比率が15%未満 | 新規個別株は原則小さくする |
| 個別株比率が10〜15%を超過 | 個別株追加より重複・整理候補を確認する |
| 株式系合計が高い | AAPL / QQQ などは既存INDEXとの重複を確認する |
| 候補が急騰後 | 追いかけず、押し目・材料・決算を確認する |

## 次に見る順番

1. Executive Summary で今週の基本方針を確認する。
2. Portfolio Guardrails で新規リスクを取れる余地を確認する。
3. Candidate Comparison で候補の優先順位と注意点を確認する。
4. Deep Dive Cards で反証と確認する数字を見る。
5. If / Then Decision Rules で今週の行動を決める。
