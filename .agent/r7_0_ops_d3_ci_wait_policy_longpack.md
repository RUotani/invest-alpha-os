# R7.0-Ops-D3: CI wait policy and run-list read-only integration

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。

## 1. State Capsule

- latest main: `2572f16`
- Ops-D2: PR #51 merged
- branch: `work/r7-0-ops-d3-ci-wait-policy`
- 目的: `gh run list` read-only + CI wait policy

## 2. 必須

- `--wait-ci` / `--ci-timeout-seconds` / `--ci-poll-seconds`
- default 待機なし
- auto-merge 禁止維持
- mock tests only
