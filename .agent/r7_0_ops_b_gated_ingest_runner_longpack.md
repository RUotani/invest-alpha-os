# R7.0-Ops-B: gated ingest runner task foundation

## 0. 最重要ルール

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。
通常文・表・箇条書きをコードブロック外に分散しないでください。

## 1. State Capsule

- repo: `/Users/uotani/Projects/invest-alpha-os`
- latest main: `9fc2f51`
- Ops-A: PR #46 merged
- 作業branch: `work/r7-0-ops-b-gated-ingest-runner`
- 目的: Ops-A operator-runnerを拡張し、J-Quants ingestのような長時間・小分け・停止条件付き処理をrunnerで扱える基盤を作る

## 2. 絶対禁止

- main direct push / force push / branch削除
- secrets / cache JSON / outputs commit
- 無ゲート live HTTP / cache write / Gmail send
- daily/signals default変更 / trading recommendation

## 3. 必須要件

- `--execute-gated` mode（dry-run default維持）
- gates: CONFIRM_LIVE_HTTP / CONFIRM_CACHE_WRITE / CONFIRM_OPERATOR_GATED_INGEST
- task YAML: config/tasks/r7_0_jquants_ingest_gated_smoke.yaml
- checkpoint/resume + evidence
- mock/simulation tests only（real live ingest なし）
