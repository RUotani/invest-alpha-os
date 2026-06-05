# Workflow Approval Boundary Pack — 2026-06-06

## Why workflow change is needed

CI artifact に `weekly_candidate_brief.json` を含め、v101 checklist と local verify の期待と一致させる。

## Exact file paths

- `.github/workflows/weekly_candidate_brief.yml`（upload-artifact `path` のみ）

## Exact patch

`docs/proposals/2026-06-06_weekly_workflow_artifact_patch_proposal.md` 参照。

## Risks

- upload path 追加により artifact サイズ微増
- 誤 path 指定で upload step が warn/fail する可能性

## Rollback

- 追加した `reports/*/weekly_candidate_brief.json` 行を削除して revert

## Tests

- merge 後の次回 run で `/tmp` download + `weekly-artifact-local-verify`
- `tests/test_weekly_artifact_schema_contract.py`

## Approval checklist

- [ ] 人間が workflow 変更を明示承認
- [ ] Hard Gate: workflow_dispatch は観測目的以外で使わない
- [ ] merge 後 read-only で artifact 確認
- [ ] Actual Import Readiness 0% 維持

## Do not apply without approval

Cursor / Agent は本パックを作成するのみ。`.github/workflows/*` への直接編集は禁止。

## Status（2026-06-06 Post #494）

- **APPROVAL_REQUIRED** — boundary pack 有効、workflow 未変更
- scheduled observation: **NOT_YET_OBSERVABLE**（2026-06-06 07:30 JST 以降に再観測）
- merge 後検証: read-only `gh run download` + `weekly-artifact-local-verify`（Hard Gate 遵守）
