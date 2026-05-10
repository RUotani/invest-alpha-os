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

### Task 1 — 完了（J-Quants stub・watchlist・Japan Signals）

- `docs/08_phase1a_jquants_plan.md` baseline
- `JQuantsStubAdapter`、`jp_equity`、`themes` 付き watchlist、daily「Japan Signals」

### Task 2 — 完了（real-mode skeleton + 安全ゲート）

- **`JQuantsClient`** + **`safe_auth_status()`**（**トークン実値・パスワード・raw を CLI に出さない**）
- **`debug jquants-status`**: **HTTP しない**
- **`debug jquants-daily-quotes --live`**: 実 HTTP は **`JQUANTS_ALLOW_LIVE_HTTP=true` とセット**の二重ゲート
- **`make verify` / GitHub Actions**: 実接続なし

**計画・運用詳細**: [08_phase1a_jquants_plan.md](./08_phase1a_jquants_plan.md)

### Task 3 以降（未着手）

- トークン期限・自動 refresh、レスポンス正規化、追加エンドポイント

---

関連: [07_ai_development_workflow.md](./07_ai_development_workflow.md)
