# Cursor Final Report — v1.0 First-Use Stabilization

作成: 2026-06-07 JST

## 結論

初日運用の固定入口を **`reports-private/manual_issue/latest/README_FOR_USER.md`** に統一。scheduled / Gmail ブロッカーは別記録とし、初日運用は **停止しない**。

## Main State

- base main（作業前）: `ddfa923bb330dac4b6fe2282ec460bee415d62e0`
- v1_usable_tomorrow: **true**
- hard gate violation: **none**

## 実施内容

1. `manual_issue/latest/` 入口（README + pointer.json）を追加
2. `manual_issue/README.md` 索引を追加
3. `docs/v1_0_operator_start_here.md` を latest 導線に更新
4. `docs/v1_0_tomorrow_operational_checklist.md` に固定入口を追記
5. 285A / AAPL / QQQ を **深掘り候補（非売買指示）** と明記

## 別ブロッカー

| 項目 | 状態 | 初日運用 |
| --- | --- | --- |
| scheduled run | pending / non-fire | 継続可 |
| Gmail | NO_GO not sent | 継続可 |

## ユーザーが読むファイル（1つ）

`reports-private/manual_issue/latest/README_FOR_USER.md`

## Safety

未実行: workflow_dispatch, workflow 変更, real email, live HTTP, cache write, import, broker, trading action
