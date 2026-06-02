# v90 Signal Candidate Pipeline Traceability Pack

## 背景
v87時点で候補0件時の表示は改善済みだったが、候補がどの段階で止まったかを定量で追跡できず、
「signal/candidate pipelineが空洞」「候補0件の根拠が弱い」というCritical指摘が残っていた。

## Claude Review Critical Finding
- 前段候補数が不明
- coverage不足 / score未達 / veto の段階別件数が追跡不能
- veto reason log が構造化されていない

## Purpose
週次レポートを observation-only のまま維持しつつ、候補パイプラインの段階別トレースを構造化して、
候補0件または少数候補の根拠を短時間で検証できる状態にする。

## Trace Data Model
- `CandidateTraceInput`
- `CandidatePipelineTraceSummary`
- `VetoReasonLog`
- 実装: `src/invis_alpha_os/product/weekly_candidate_pipeline_trace_v90.py`

## Stage Counting Rules
- `input_count`: 入力候補総数
- `coverage_missing_count`: coverage不足または data_insufficient
- `score_miss_count`: coverage通過後にscore閾値未達
- `veto_count`: veto理由が1件以上の候補数
- `final_candidate_count`: score通過かつvetoなしの「深掘り可能候補」

`final_candidate_count` は買い推奨数ではなく、深掘り入口の候補数として扱う。

## Weekly Report Integration
`weekly_candidate_brief_v0.py` の copy-ready/markdown 出力へ以下を追加:
- `## 候補パイプライン・トレース`
- 入力 / coverage不足 / score未達 / veto該当 / 深掘り可能候補 テーブル
- `Veto reason log` テーブル（または該当なしメッセージ）
- 候補0件時の非推奨明示（買い推奨ではない）

## Email Preview Treatment
`weekly_candidate_brief_email.py` で copy-ready から短縮要約を抽出し、txt/htmlへ反映:
- 候補パイプライン行
- 主因と次確認行

本文を肥大化させず、短縮要約のみを追加。

## Safety Boundary
本変更は source-only / fixture-only:
- workflow変更なし
- provider live HTTP / market-data live fetch なし
- cache write / actual import なし
- broker API / env-secret表示 なし
- dependency/pyproject/Makefile変更なし
- trading action / order placement / 実メール送信なし

## Tests
- `tests/test_weekly_candidate_pipeline_trace_v90.py`
- `tests/test_weekly_candidate_brief_v0.py`
- `tests/test_weekly_candidate_brief_email.py`
- 回帰確認: `tests/test_target_allocation_gap_calculator_v82.py` / `tests/test_monthly_decision_sheet_v84.py`

## Next Actions
- v90 PRのCI green確認後、人間レビューへ回す
- v86 scheduled run observationでartifact反映を検証する
