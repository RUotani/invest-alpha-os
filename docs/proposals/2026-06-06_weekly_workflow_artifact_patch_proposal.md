# Weekly Workflow Artifact Patch Proposal

## Problem

1. CI artifact upload に `weekly_candidate_brief.json` が含まれない（runner は #475 以降で生成するが upload path 未登録）
2. natural schedule run が未観測のため、scheduled artifact の実証が pending

## Evidence

- `.github/workflows/weekly_candidate_brief.yml` upload `path` に JSON なし
- dispatch run `26803119044` artifact: md/copy/email/status のみ（JSON なし）
- `docs/decisions/2026-06-06_weekly_artifact_status_gap_analysis.md`
- `reports-private/scheduled_observation/weekly_artifact_missing_analysis_20260606.md`

## Proposed Patch

`weekly_candidate_brief.yml` の Upload step に 1 行追加:

```diff
           path: |
             reports/*/weekly_candidate_brief_v0_1.md
             reports/*/weekly_candidate_brief_copy.md
+            reports/*/weekly_candidate_brief.json
             reports/*/email/*
             outputs/operator/weekly_candidate_brief/*/status.json
```

## Files likely affected

- `.github/workflows/weekly_candidate_brief.yml`（upload-artifact `path` のみ）

## Exact diff / copy-ready patch

```yaml
      - name: Upload weekly candidate brief artifact
        uses: actions/upload-artifact@v4
        with:
          name: weekly-candidate-brief
          path: |
            reports/*/weekly_candidate_brief_v0_1.md
            reports/*/weekly_candidate_brief_copy.md
            reports/*/weekly_candidate_brief.json
            reports/*/email/*
            outputs/operator/weekly_candidate_brief/*/status.json
```

## Safety Gates

- upload path 追加のみ（runner ロジック変更なし）
- workflow_dispatch 不要
- cache write / import / broker / live HTTP なし
- merge 後の次回 schedule/dispatch で JSON が artifact に含まれることを read-only 確認

## Approval Required

- `.github/workflows/*` 変更は **人間明示承認** が必要（Hard Gate）
- 適用前に `docs/proposals/2026-06-06_workflow_approval_boundary_pack.md` を確認

## Why not applied automatically

Cursor Long-Run Max 方針: workflow 直接変更禁止。copy-ready proposal のみ作成。

## Status（2026-06-06 Post #494）

| 項目 | 状態 |
| --- | --- |
| patch 適用 | **未適用** |
| 承認 | **APPROVAL_REQUIRED**（Hard Gate） |
| natural schedule 観測 | **NOT_YET_OBSERVABLE**（07:30 JST 未到達） |
| 次アクション | 人間承認後に workflow upload path 1行追加のみ |

Post #494 Long-Run: proposal 更新のみ実施。workflow ファイルは変更していない。
