# Decision — Weekly Artifact / status.json Gap Analysis (2026-06-06)

## 結論

`weekly_candidate_brief.json` 未生成の主因は **runner script が JSON 出力を呼んでいなかった** こと。  
CLI（`weekly-candidate-brief --format json`）と v104 schema は既に対応済みだった。

## 原因

| 層 | 状態 | 詳細 |
| --- | --- | --- |
| CLI | OK | `--format json` 実装済み |
| v104 status | OK | `reports.json_report` フィールドあり、`--json-report` 対応 |
| `run_weekly_candidate_brief.sh` | **欠落** | markdown/copy のみ生成、JSON 未呼び出し |
| GitHub workflow upload | **未対応** | artifact path に `weekly_candidate_brief.json` 未記載 |

## 実施した source-only 修正（#475 予定）

- `scripts/run_weekly_candidate_brief.sh` に JSON 生成ステップ追加
- v104 status 書き込み時に `--json-report` を渡す
- script smoke test 更新

## workflow 変更なしで残るギャップ

- CI artifact ダウンロードに JSON が含まれない（`.github/workflows/weekly_candidate_brief.yml` の upload path 制限）
- **対応**: 人間承認後に workflow の upload `path` に `reports/*/weekly_candidate_brief.json` を追加する必要あり
- 現時点では runner 実行時にローカル/CI 上で JSON は生成され、status.json の `reports.json_report` にパスが記録される

## Safety

- workflow 変更なし
- workflow_dispatch なし
- cache write / live HTTP / import なし
