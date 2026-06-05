# Weekly Artifact Missing Analysis — 2026-06-06

## Summary

natural `event=schedule` run が未観測のため、**scheduled artifact bundle は存在しない**。  
参考として read-only で `workflow_dispatch` run `26803119044`（2026-06-02）の artifact を `/tmp` に取得し比較した。

## Dispatch Reference Artifact（read-only, 2026-06-02）

| File | Present |
| --- | --- |
| `weekly_candidate_brief_v0_1.md` | yes |
| `weekly_candidate_brief_copy.md` | yes |
| `weekly_candidate_brief.json` | **no** |
| `email/email_preview.txt` | yes |
| `email/email_preview.html` | yes |
| `email/email_preview.eml` | yes |
| `outputs/.../status.json` | yes（**旧 minimal schema** — v104 フィールドなし） |

## status.json（dispatch 参考）

- `schema_version`: **なし**（v104 導入前の run）
- `gmail_send_attempted`: **フィールドなし**
- `reports.json_report`: **なし**

## Local Verification Contract（現 main）

`weekly-artifact-local-verify` + v101/v104 fixture では以下を期待:

- v104 `status.json`（`gmail_send_attempted=false`）
- markdown / copy / email preview
- `weekly_candidate_brief.json`（runner #475 以降）

## Gaps

| Gap | Layer | Status |
| --- | --- | --- |
| schedule run 未観測 | GitHub Actions | pending（2026-06-06 07:30 JST 以降） |
| JSON 未 upload | workflow upload path | proposal 作成済み、未適用 |
| 旧 dispatch status.json | historical run | v104 以前の artifact |

## Source-Only Next Action

1. schedule success 後に `/tmp` download → `weekly-artifact-local-verify`
2. workflow patch は `docs/proposals/2026-06-06_weekly_workflow_artifact_patch_proposal.md` を人間承認後に適用

## Safety

- artifact 本体は repo 未コミット
- workflow 未変更
