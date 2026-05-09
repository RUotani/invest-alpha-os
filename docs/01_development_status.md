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

## Phase 1a — 未着手（候補）

次フェーズの候補は [06_phase0_completion_report.md](./06_phase0_completion_report.md) の「Phase 1a」を参照。このドキュメントは Phase 1a キックオフ時に再度更新する。
