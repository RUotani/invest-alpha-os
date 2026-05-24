# RULES §5 veto path — documentation reconciliation

日付: 2026-05-24  
ステータス: approved  
関連: `RULES.md` §5, `docs/156_product_signals_inventory_rules_gap.md`

## 結論

- `veto_rules` の実装は `risk/veto_rules.py` に置いたまま維持する。
- `RULES.md` §5 の `signals/veto_rules.py` 表記は **ドキュメント drift** として認識し、次回 RULES 改定 PR（人間承認）で `risk/veto_rules.py` に合わせる。
- ファイル移動は行わない（import 破壊リスク > 文言整合）。

## 確度

- 90%

## 反証

- operator ゲート解除のため `signals/` へ symlink/再export が必要と判明した場合は supersede。

## 次のアクション

- [ ] 人間: RULES.md §5 1行修正 PR（任意）
- [x] docs/156 + 本 decision で drift を固定
