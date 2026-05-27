# Weekly Observation Report v1 を完成判定ゲートとする

日付: 2026-05-27
ステータス: approved
関連ファイル: `STATE.md`, `src/invis_alpha_os/product/weekly_observation_report_v1.py`, `docs/decisions/README.md`

## 結論(1〜3行)
- **P3 live forward usable**（`matched_normal` 10/10）は短期開発 KPI から外し、**time-dependent monitoring gate** として扱う。
- **Weekly Observation Report v1** を invest-alpha-os 短期開発の唯一の完成判定対象とする。
- portfolio readiness（P0–P2）は P3 live forward 成熟に**完全依存させない**（P3 は監視・補助情報）。

## 確度
- 90%

## 背景
- `matched_normal=1/10` の状態で P3 usable を短期完了条件にすると、docs/handoff/health/smoke 等の周辺作業が増え、投資判断支援 OS の「毎週読むレポート」完成から逸れる。
- 残り 9 サンプルは ISO 週書き込み・cache 経過・horizon 成熟など**データ時間依存**であり、コーディングだけでは解決しない。

## 検討した選択肢
1. P3 usable 到達まで開発継続（現状に近い）
2. Weekly Observation Report v1 を完成判定にし、P3 は監視ゲートに格下げ（**採用**）
3. historical backfill を今すぐ実装して P3 を人工的に満たす

## 採用した選択肢の根拠
- 毎週人間が読む 1 枚の観測レポートが、観察モード OS の実用完成定義に最も近い。
- P3 は引き続き `forward-p3-status` / `p3-path-to-usable` / weekly dry-run で**正直に未成熟を表示**する。
- historical backfill は別検討とし、今回は**実装しない**。

## 反証(bear case)
- レポート v1 が P3 未成熟を隠すと、完成判定が早すぎる。→ v1 レポートに **P3 monitoring gate** セクションを必須化。
- portfolio 70%（L3）承認タイミングが曖昧になる。→ usable 到達後の L3 再承認は従来どおり decision / STATE に残す。

## 影響範囲
- 新 CLI: `weekly-observation-report-v1`
- 新 product モジュール: `weekly_observation_report_v1.py`
- sample: `reports/YYYY-MM-DD/sample_weekly_observation_report_v1.md`
- `portfolio_readiness` の milestone ロジックは変更しない（表示・decision で依存関係を明文化）

## 次のアクション
- [x] Weekly Observation Report v1 実装
- [x] sample report 生成
- [ ] 人間 MERGE / STOP 判断（sample のみ参照）
