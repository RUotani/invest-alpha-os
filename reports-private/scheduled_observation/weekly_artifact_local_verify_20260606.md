# Weekly Artifact Local Verify — 2026-06-06

## Summary

| 項目 | 結果 |
| --- | --- |
| verify time | 2026-06-06 00:22 JST |
| source | dispatch run `26803119044`（2026-06-02, reference only） |
| artifact root | `/tmp/invest-alpha-os-weekly-dispatch-26803119044` |
| report_date | 2026-06-02 |
| ready | **false**（旧 dispatch artifact · pre-#487 markers） |
| status.json | 存在（download 内 `outputs/operator/.../status.json`） |
| weekly_candidate_brief.json | **missing**（workflow upload gap · 既知） |

## Classification

| Case | 判定 |
| --- | --- |
| status.json present | **PASS**（ファイル存在） |
| email preview txt/html | **PASS**（存在） |
| copy/md markers（現行 v101） | **WARN**（旧 artifact · Score/Veto 等マーカー不足） |
| JSON report | **GAP**（CI upload 未登録） |

## Command Used

```bash
gh run download 26803119044 --dir /tmp/invest-alpha-os-weekly-dispatch-26803119044
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-artifact-local-verify \
  --report-date 2026-06-02 \
  --report-dir /tmp/invest-alpha-os-weekly-dispatch-26803119044/weekly-candidate-brief/reports/2026-06-02 \
  --status-file /tmp/invest-alpha-os-weekly-dispatch-26803119044/weekly-candidate-brief/outputs/operator/weekly_candidate_brief/2026-06-02/status.json \
  --json-report-optional \
  --format markdown
```

## Interpretation

- dispatch 参考 artifact は **現行 v1.0 契約とは不一致**（#487 以前の生成物）。
- natural scheduled success 後の **新 artifact** で再検証が必要。
- workflow JSON upload 承認後は `--require-json-report` も再評価。

## Next Actions

1. 2026-06-06 07:30 JST 以降の `event=schedule` success artifact で再 verify
2. 承認後 workflow patch → JSON upload 確認
3. ready=true になったら Report MVP の observation 項目を更新

## Safety

- workflow_dispatch: **未実行**（既存 dispatch run の download のみ）
- artifact を repo へコミット: **なし**
