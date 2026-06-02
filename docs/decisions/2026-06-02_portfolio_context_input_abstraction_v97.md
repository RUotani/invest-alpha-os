# v97 Portfolio Context Input Abstraction Pack

## なぜ必要か
v95/v96時点で、portfolio前提（現金比率、個別株比率、guardrail、目標配分）が複数箇所に分散し始めた。
v97では redacted fixture 前提の入力契約を明示化し、週次・月次・候補判定で同じ前提を追跡できるようにする。

## v95 Monthly Input Consistency との関係
- v97 contract から v95 input へ変換する関数を追加した。
- v95検証の主要 warning（cash minimum 未満、個別株 target band 超過）が v97経由でも再現されることをテストで保証した。

## v96 Weekly/email Shared View Model との関係
- v97は portfolio context summary line を供給できる契約として追加。
- 今回は大改造を避け、v96への直接注入は必須化せず、将来接続可能な独立契約として整備した。

## 扱わない範囲
- raw Excel direct parsing
- broker export / broker API
- actual import / live fetch / cache write

上記は未承認領域のため、v97では source-only / fixture-only 境界を維持する。

## redacted fixture と将来入力境界
- v97 fixture は 2026-05 redacted portfolio context を固定値で保持。
- 将来は sanitized/manual input 経由の差し替えを想定し、入力契約のデータ構造を先に固定する。

## v86 scheduled run observation との関係
v86での artifact review 時に、portfolio前提の出所を追跡しやすくするための前段整備として v97 を位置付ける。
