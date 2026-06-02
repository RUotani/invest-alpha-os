# v84 Monthly Decision Sheet Pack

Date: 2026-06-02

## 背景

v78 の redacted portfolio context と v82 Target Allocation Gap Calculator により、
配分超過/不足の数値化は可能になった。
ただし、月次の意思決定（買う/売る/保留/現金回復/整理候補）を
一画面で記録・レビューする Markdown シートが未整備だった。

## 目的

月次ポートフォリオ判断を、観測・記録用の意思決定シートとして出力する。
出力は売買指示ではなく、制約認識と判断ログの整備を目的とする。

## Inputs

- v78 redacted portfolio context（2026-05 month-end）
  - 総資産 4,327.9万円
  - 現金 508.2万円 / 11.7%
  - 株式系 2,934.5万円 / 67.8%
  - 個別株 846.3万円 / 19.6%
  - 債券 582.7万円 / 13.5%
  - 暫定オルタナ 302.5万円 / 7.0%
- guardrail/target
  - 現金 15% / 20% / 30%
  - 株式系 49.0%
  - 個別株 10〜15%
  - 債券 10.5%
  - オルタナ 10.5%

## Output Sections

- 今月の結論
- 判断サマリー
- 今月の意思決定テーブル
- 現金回復ステップ
- 次月への持ち越し
- 配分ギャップ（v82再利用）
- Safety note

## Calculation Dependencies

- `src/invis_alpha_os/portfolio/target_allocation_gap_calculator_v82.py` を再利用
- v84 は standalone markdown generator として実装
  - `src/invis_alpha_os/portfolio/monthly_decision_sheet_v84.py`

## Safety Boundary

本機能は source-only / observation-only であり、以下は実行しない:

- workflow 変更
- provider live HTTP / market-data live fetch
- cache write
- actual import
- broker API / raw broker export parsing
- env/secret 表示
- dependency / pyproject / Makefile 変更
- trading action / order placement / auto trading

## Why This Is Not Trading Advice

シート本文に以下を明記する。

- このシートは売買指示ではなく、ポートフォリオ制約に基づく意思決定補助・記録用
- 実際の売買は、価格・税金・NISA枠・取得単価・家計キャッシュフロー・リスク許容度を別途確認して判断

## Tests

- `tests/test_monthly_decision_sheet_v84.py`
  - 必須セクション
  - 主要数値（11.7%、19.6%、67.8%、不足141/357/790、+813.8、+197.1、+128.3、151.9不足）
  - Safety 文言
  - 禁止語（買うべき/売るべき等）の非含有
- 既存 v82 テスト再実行
  - `tests/test_target_allocation_gap_calculator_v82.py`

## Next Actions

1. PR で CI green を確認し、人間承認後に merge
2. scheduled run 観測後、月次シートの運用導線（必要なら CLI 追加）を検討

