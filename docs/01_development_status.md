# Development Status

## Phase 0-v1.1 — 完了（クローズ済み）

Phase 0-v1.1 は完了し、以下条件を確認済み。

- ローカルで `PYTHON=.venv/bin/python make verify` が成功すること
- GitHub Actions の `tests` workflow がグリーンであること
- `outputs/` は `.gitkeep` 等の最小限のみ Git 管理し、実行生成物は原則コミットしないこと
- `src/invis_alpha_os/data/` が Git 管理対象であり、CI で `invis_alpha_os.data` の import エラーが出ないこと
- **Observation Only + Shadow Portfolio**、**No Auto Trading** の方針を維持すること

### 完了サマリ

- 拡張可能なパッケージ骨格（`data` / `risk` / `portfolio` / `observation` 等）
- 設定テンプレート（watchlist、veto、data_confidence、market_data 等）
- CLI（`alpha-os`）と PATH 非依存の `make verify`
- Actions: `make test` + `PYTHON=python make verify`

**詳細な完了記録・障害対応一覧**: [06_phase0_completion_report.md](./06_phase0_completion_report.md)

---

## Phase 1a — 進行中

### Task 1 — 完了内容（J-Quants 準備・stub）

- `docs/08_phase1a_jquants_plan.md`: J-Quants の段階設計・非 Git 運用・取得したいデータの整理
- `JQuantsStubAdapter`（`src/invis_alpha_os/data/adapters/jquants_stub.py`）: **`JQUANTS_ENABLED=false` で HTTP なし・落ちない**
- `config/market_data.yaml`: トップレベル **`jp_equity`**（primary: jquants, `enabled: false`）
- `config/watchlist.yaml`: 日本株 11 銘柄＋ **`themes`** 付き
- `.env.example`: J-Quants 関連プレースホルダ（**実値なし**）
- **daily report**: 「**## Japan Signals**」セクション追加（stub）
- まだ **J-Quants に実 API 接続しない**／**自動売買なし**

**計画詳細**: [08_phase1a_jquants_plan.md](./08_phase1a_jquants_plan.md)

### Task 2 以降（未着手）

- 実トークン取得・HTTP 実装・テストでのモック化（運用・セキュリティ合意後）

---

関連: [07_ai_development_workflow.md](./07_ai_development_workflow.md)
