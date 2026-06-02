# v96 Weekly/email Shared View Model Pack

## なぜshared view modelが必要か
v90-v95で週次本文とemail previewに要約要素が増え、表示ロジックの重複と文言ズレのリスクが上がった。
v96では shared view model を導入し、同じ意味論を両チャネルで再利用可能にする。

## weekly reportとemail previewで共通化する範囲
- Score / Veto の短縮要約
- 候補パイプライン短縮要約
- Monthly Input Consistency の短縮要約
- 安全文言（売買指示ではない）

## 共通化しない範囲
- weekly本文の詳細テーブル（長表）
- emailの個別候補カード詳細（compact優先）
- レンダリング固有のHTML装飾

## source-only / fixture-only boundary
- fixture由来のsummaryを共有し、live data依存を追加しない
- workflow・dependency・external IOは変更しない
- raw Excel direct parsing、actual import、cache write は行わない

## v86 scheduled run observationとの関係
v86ではartifact観測が主目的であり、v96はその前段として weekly/email の表示一貫性を高める。
scheduled artifact review時の比較観点を簡素化できる。

## 将来のPortfolio Context Input Abstractionへの接続余地
shared view model は summary line の供給点を一箇所化するため、
将来 Portfolio Context Input Abstraction を導入しても weekly/email の表示契約を保ちやすい。
