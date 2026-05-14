# R6.9-C — 優先順位メモ（US / metals / macro / portfolio）（調査のみ・実装なし）

**ステータス**: 優先度の整理のみ。**コード変更・live HTTP・production cache write は対象外**。本文は **`main` に反映済み**（R6.9-C 取り込みコミット `61b3bf2`）。

---

## 1. 目的

投資 OS 拡張のうち、**US 株（US equities）**・**metals（貴金属等のコモディティ／代替リスク）**・**macro（マクロ）**・**portfolio（ポートフォリオ連携）**の四領域について、**既存ドキュメントと現状スコープ**を踏まえた **着手順のたたき台** を固定する。

---

## 2. 推奨優先順位（高 → 低）

| 順位 | 領域 | 理由（要約） |
|:----:|------|----------------|
| 1 | **US 株** | 既に **Stooq 経由のキャッシュ・プレビュー・手動バッチ** など実装・設計資産が厚い（`docs/11` / `docs/12` / `docs/13` / `docs/14` / `docs/15` 系）。**観測専用**の延長で他領域への依存が少ない。 |
| 2 | **portfolio 連携** | **Shadow portfolio**・**Observation only** 方針と整合しやすい。**自動売買なし**のまま、リスク・証跡の「束ね方」を段階的に強化できる。 |
| 3 | **macro** | データソース・定義が広く、**誤った単一指標への依存**リスクが大きい。US・portfolio の観測基盤が安定してからでも遅くない。 |
| 4 | **metals** | **US ETF（例: GLDM）やコモディティプロキシ**は既存 US キャッシュに触手があるが、**専用データライン**や **為替・保管コスト**など論点が増えやすい。**US 周辺が固まった後**に切り出すと安全。 |

---

## 3. 既存アンカー（参照のみ）

- 全体カバレッジ: [docs/10_investment_os_coverage_map.md](./10_investment_os_coverage_map.md)
- US 計画: [docs/11_us_market_data_provider_plan.md](./11_us_market_data_provider_plan.md)
- 失敗時オペレーション: [docs/12_us_provider_failure_operator_playbook.md](./12_us_provider_failure_operator_playbook.md)
- スケジュール ingest 安全設計: [docs/13_us_provider_scheduled_ingest_design.md](./13_us_provider_scheduled_ingest_design.md)
- 手動バッチ: [docs/14_us_provider_manual_live_batch_smoke_design.md](./14_us_provider_manual_live_batch_smoke_design.md)

---

## 4. 次の一手（実装はしない）

1. ChatGPT / 人間レビューで本メモの順位を確定する。  
2. 確定後、**最小スコープのタスク**（例: US の観測 CLI の一行改善のみ）を **別ブランチ**で切る。  
3. **`main` 取り込み**は従来どおり **早送り取り込み**と **CI 緑**をゲートにする。
