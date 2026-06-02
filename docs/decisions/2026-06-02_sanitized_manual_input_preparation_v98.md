# v98 Sanitized / Manual Input Preparation Pack

## なぜv98が必要か
v97で portfolio context の入力契約は整備されたが、raw Excel / broker export / actual import へ進む前に、
手入力相当の sanitized data を安全に通す中間契約が必要になった。

## raw Excel / broker dataへ進む前にsanitized/manual inputを挟む理由
- Hard Gateに触れずに入力契約の整合性を先に検証できる
- source-only / fixture-only で検証可能なため再現性が高い
- 後段（v97/v95/v96）への接続を壊さずに段階導入できる

## v97 Portfolio Context Input との関係
- v98入力から `PortfolioContextInputV97` へ変換する経路を追加
- 既存 v97 guardrail と target allocation を引き継ぐ

## v95 Monthly Input Consistency との関係
- v98入力から v95 monthly input に変換し、warning parity を検証
- cash minimum 未満 / 個別株 target band 超過が同様に出ることを保証

## v96 Weekly/email Shared View Model との将来接続
- v98 summary lines を提供し、将来 v96 shared view model に差し込めるよう準備
- 今回は大規模配線変更は行わず、契約定義に留める

## Hard Gates
- workflow変更、manual workflow_dispatch、live HTTP、cache write、actual import、broker API、
  raw Excel direct parsing、env/secret表示、dependency変更、trading action、実メール送信は実行しない

## まだactual importをしない理由
actual import は raw data 境界・認証・監査要件を伴うため、別承認と安全設計が必要。
v98では sanitized/manual input 契約と検証のみに限定し、境界を明確化する。
