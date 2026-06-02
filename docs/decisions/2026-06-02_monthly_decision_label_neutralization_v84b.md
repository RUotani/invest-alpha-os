# v84b Decision Label Neutralization Pack

## 背景

v84a review で、月次意思決定シートは機能・数値整合・安全表現とも有効であることを確認した。
一方で、意思決定テーブルの一部ラベル（例: 「買う（新規個別株追加）」）は、
文脈上は抑制方針でも、見出し語だけで売買指示に見える誤読リスクが残っていた。

## 目的

月次意思決定シートのテーブル見出しと判断ラベルを中立化し、
「確認・記録・リスク管理」の分類であることを明確化する。

## Changed Labels

- テーブル見出し
  - `| アクション | 判定 | 理由 | 次に確認すること |`
  - -> `| 判断領域 | 月次スタンス | 理由 | 次に確認すること |`

- 行ラベル
  - `買う（新規個別株追加）` -> `新規個別株リスク`
  - `保留（インデックス積立）` -> `インデックス積立方針`
  - `保留（債券追加）` -> `債券ポジション`
  - `保留（GOLD/オルタナ追加）` -> `オルタナティブ配分`
  - `整理候補` -> `既存ポジション確認`

- 月次スタンス
  - `原則しない` -> `新規リスク拡大を抑制`
  - `今月は急がない` -> `追加判断を急がない`
  - `慎重` -> `配分余地はあるが慎重`

## Safety Boundary

本変更は source-only / wording-only の中立化であり、以下は不実施:

- workflow変更
- provider live HTTP / market-data live fetch
- cache write / actual import
- broker API / raw broker export parsing
- env/secret 表示
- dependency / pyproject / Makefile変更
- trading action / order placement / 自動売買
- 実メール送信

## Why This Reduces Misread Risk

「買う/売る」連想語を避け、判断文脈を
「リスク」「方針」「配分」「既存ポジション確認」に寄せることで、
月次シートが売買指示ではなく確認・記録分類であることを読み手に伝えやすくなる。

また、Safety note に以下趣旨を追加して誤読を抑制した。

- この表の「月次スタンス」は確認・記録・リスク管理のための分類であり、売買指示ではない

## Tests

- `tests/test_monthly_decision_sheet_v84.py`
  - 中立化後ラベルの存在
  - 旧ラベル非含有
  - 新テーブル見出し確認
  - Safety note 強化文言確認
  - 既存セクション・数値整合の維持

## Next Actions

1. v84b PR を CI green で review し、人間承認後に merge
2. scheduled run 観測で、週次/月次の安全文言整合を継続確認

