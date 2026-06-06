# v1.4 Early Discovery Gap Review — Claude Proposal vs #508

## 3行サマリー

- Claude Step 1はEarly Discovery operational definitionでcloseする。
- Claude Step 2/3は#508で完了済み。本PRは再実装しない。
- Step 4以降の実データ接続・validationはHard Gateまたは将来作業として残る。

## Gap Review

| Claude Step | 状態 | 根拠 / 次アクション |
|---|---|---|
| Step 1: Early Discovery定義 | Closed by this decision | `docs/decisions/2026-06-06_early_discovery_operational_definition.md` |
| Step 2: Theme dictionary / candidate roles | Completed by #508 | v1.4 theme dictionary、Phase × Role |
| Step 3: classifier precedence / 285A分離 | Completed by #508 | portfolio gate → hard overheat → veto → early score → theme proxy |
| Step 4: price/volume connection | Not executed | live price/volume fetchはHard Gate。fixture-only pure metricsまで実装 |
| Step 5: fundamentals / revisions / theme flow | Future | nullable contractを維持して別設計 |
| Step 6: real-data validation / calibration | Future | 実データ承認とvalidation evidenceに接続し、performance claimは禁止 |

## #508 Non-Duplication Boundary

本PRは以下を再実装しない。

- Theme dictionary
- Candidate roles
- Phase × Role classifier
- 285A Theme Proxy / Do Not Chase分類
- weekly report v1.4 UI

追加範囲は、fixture-only価格出来高メトリクス、nullable Early Discovery score skeleton、定義docs、将来承認proposal、contract testsに限定する。

## Remaining Gaps

- read-only price/volume sourceの承認
- corporate action調整の検証
- benchmark選定とtheme-level集計
- 実データ上のfalse positive / false negative評価
- score重みの較正

fixture出力はperformance evidenceではない。
