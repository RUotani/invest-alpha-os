# v95 Monthly Input Consistency Hardening Pack

## 背景
v94までで週次レポートの表示整備は進んだが、月次入力データの契約検査（単位・月次・純資産整合・配分比率・ガードレール）が
明示的に再利用可能な形で定義されていなかった。

## なぜv95が必要か
- 月次入力が壊れていても見た目だけで判断が進むリスクを下げる
- 週次/ 月次の判断根拠を共通契約で接続しやすくする
- 2026-05 修正版ポートフォリオ前提の整合性を fixture-only で再現可能にする

## raw Excel direct parsingを行わない理由
- v95は入力契約の検査層を固める段階であり、raw Excelやbroker export直結は安全境界外
- source-only / fixture-only で挙動を固定し、CIで再現可能性を優先する

## redacted fixtureで検査する範囲
- as_of_month の妥当性（欠損/未来/古さ）
- 単位契約（万円）
- 総資産・ローン残高・純資産の一致
- 資産分類金額合計と総資産の一致
- 資産分類比率合計の整合
- 株式系合計と INDEX + 個別株 の一致
- 現金比率 / 個別株比率ガードレール

## ERROR / WARN / INFO の意味
- ERROR: 入力契約として不整合。月次判断に使用しない
- WARN: 判断は可能だが、人間確認または補正を優先
- INFO: 方針上の注意・ガードレール確認

## 現金比率・個別株比率 guardrail
- 現金 minimum: 15%
- 現金 preferred recovery zone: 20%
- 個別株 target band: 10〜15%
- 2026-05 fixture は `cash 11.7%` / `single stock 19.6%` のため WARN が期待される

## v86 scheduled run observationとの関係
- v86では scheduled artifact の表示確認を行う
- v95はその前段として、月次入力契約の破損検知をコード化し、artifact解釈の前提を安定化する

## 今後、実Excel/actual importを接続する際のHard Gate
- raw Excel direct parsing は別承認PRで実施
- actual import / cache write / provider live HTTP は別承認の安全境界内でのみ許可
- 接続時は v95契約を壊さないテスト（異常系含む）を必須化する
