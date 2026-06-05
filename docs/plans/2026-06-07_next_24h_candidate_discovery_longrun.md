# Next 24h Long-Run — Candidate Discovery OS

Version: 2026-06-06（Post #494 consolidation）

## 目的

Global Multi-Asset Candidate Discovery OS を主戦場として、**broker / auto-trading なし**で次の24hロングランを定義する。

## Long-Run キュー（優先順）

### Phase 1 — Observation（Hard Gate 遵守）

1. 2026-06-06 07:30 JST 以降 `weekly_candidate_brief.yml` `event=schedule` read-only 観測
2. artifact あれば `/tmp` download + `weekly-artifact-local-verify`
3. `scheduled_run_observation_20260606.md` 分類更新 PR

### Phase 2 — Discovery Product

1. **Global asset radar skeleton**（fixture-only、US/JP/ETF 横断）
2. **Theme/segment ranking**（coverage taxonomy 拡張）
3. **Candidate queue schema**（score/veto/portfolio fit フィールド）
4. **Momentum/value/macro overlay**（weekly 1行要約）
5. **Portfolio fit and veto layer**（既存 guardrail 接続、新規 operator なし）

### Phase 3 — Report Polish

1. scheduled 実 artifact vs fixture sample 差分
2. email preview 候補あり週 compact 回帰
3. monthly + weekly index（fixture-only）

### Phase 4 — Workflow（承認待ち）

- `docs/proposals/2026-06-06_weekly_workflow_artifact_patch_proposal.md`
- **APPROVAL_REQUIRED** — Cursor は適用しない

## 停止条件

| 条件 | 対応 |
| --- | --- |
| live HTTP / cache write が必要 | NO-GO 記録、fixture-only 継続 |
| workflow 変更が必要 | proposal 更新のみ |
| CI 同一原因 2回失敗 | Final Report で停止 |
| merge conflict 未解決 | Final Report で停止 |

## 安全範囲

- `signals/` / `risk/` / `portfolio/` / `reports/` の product 変更
- `docs/` / `reports-private/` の observation・readiness 更新
- read-only `gh run list/view/download`

## 関連

- `docs/project_goal_candidate_discovery_os.md`
- `docs/plans/2026-06-07_next_24h_candidate_discovery_tree.md`
