# 2026-06-02 sanitized/manual input report connection v99

## 3行サマリー
- v98 の sanitized/manual input 検証結果を weekly copy と email preview に接続した。
- v96 shared view model に sanitized summary を追加し、weekly/email の要約ソースを統一した。
- raw Excel / broker export / actual import は引き続き扱わず、source-only / fixture-only を維持する。

## 背景
v98 で sanitized/manual input 契約は整備できたが、週次レポート/メール上での可視化が不足していた。  
その結果、cash minimum 警告・single stock 警告・v95/v97 整合の確認が weekly/email 間で分断されるリスクがあった。

## 決定
- `weekly_email_shared_view_model_v96` を後方互換で拡張し、`sanitized_manual_input_summary_lines` を追加する。
- v99 ヘルパーで v98 fixture -> v97/v95 parity をまとめた compact summary を生成する。
- weekly copy は「Sanitized / Manual Input（共有要約）」を追加する。
- email text/html は「Sanitized / Manual Input（短縮）」のみ表示し、長表は出さない。

## 期待効果
- v98 -> v97 -> v95 の警告が weekly/email で同じ意味で表示される。
- 手入力/sanitized 入力レビューを raw data 前段で運用可能にする。
- 既存の観測-only安全文言を維持し、売買指示との誤解を防ぐ。

## 非対象
- raw Excel direct parsing
- broker export parsing
- actual import
- broker API / live HTTP
- cache write / reports-private raw data write

## Hard Gates
- workflow / dependency / pyproject / Makefile 変更なし
- env/secret 表示なし
- 実メール送信なし

## v86 scheduled observationとの関係
v99 は週次出力の表示契約の整備であり、v86 scheduled run observation の実行条件を変更しない。  
次回 scheduled 観測時に、sanitized summary が weekly/email artifact で一貫表示されることを確認対象に追加する。
