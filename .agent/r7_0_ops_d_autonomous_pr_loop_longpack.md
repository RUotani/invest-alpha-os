# R7.0-Ops-D: autonomous PR loop foundation

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。

## 1. State Capsule

- latest main: `134717f`（Ops-C merged）
- branch: `work/r7-0-ops-d-autonomous-pr-loop`
- 目的: task → evidence → tests → PR draft → optional `gh pr create`（自動merge禁止）

## 2. 絶対禁止

- 自動merge / `gh pr merge` / force push / secrets commit

## 3. 必須

- default dry-run: PR body draft only
- `--create-pr` + `CONFIRM_GITHUB_PR_CREATE=YES` でのみ gh pr create
- mock tests for gh subprocess
