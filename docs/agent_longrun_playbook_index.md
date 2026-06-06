# Agent Long-Run Playbook Index

版: 2026-06-06

## Cursor 作業開始時

1. `RULES.md` / `STATE.md` を読む
2. **`.agent/cursor_knowledge_longrun_playbook_20260606.md`** を読む（Long-Run 標準フロー）

## 必須運用

| 項目 | ルール |
| --- | --- |
| PR 本文 | `gh pr create --body-file` のみ（`--body "..."` 禁止） |
| stage | `git add .` 禁止 · 対象ファイルのみ |
| Final Report | `reports-private/longrun_reports/cursor_final_report_*.md` |
| チャット | 要点のみ（全文貼り付け禁止） |
| 人間確認 | 危険領域以外は自律完走 |

## 関連

- `.agent/cursor_agent_quality_efficiency_longrun_standard.md`
- `docs/decisions/2026-05-29_long_run_first_development_rule.md`
- `AGENTS.md` §2.5 Long-Run First
