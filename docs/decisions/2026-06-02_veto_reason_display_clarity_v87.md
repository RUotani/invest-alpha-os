# v87 Veto Reason Display Clarity Pack

## 背景

v81/v85/v83 で候補0件時のUXは改善済みだが、`weekly_candidate_brief` と email preview において、
coverage不足・score未達・veto・data insufficient の関係が読み取りづらいケースが残っていた。

## 目的

候補0件時に「なぜ0件か」「次に何を確認するか」を短時間で把握できるようにし、
veto該当が0件でも「買える」判断に誤読されない表示へ寄せる。

## Display Rules

- 候補0件時は `候補0件の理由メモ` を出し、coverage/score/veto を行単位で表示する。
- `件数` だけでなく `状態` を併記し、score側の判定保留を曖昧にしない。
- copy-ready には短縮メモを追加する。
  - `候補0件の主因: ...`
  - `次確認: ...`
- vetoが0件の場合は「vetoで除外されていないが、新規追加判断に進まない」趣旨を明示する。

## Candidate-Zero Reason Categories

- coverage不足: data insufficient候補はcoverage不足として扱う。
- score未達: coverage/veto確認優先の状態も明示する。
- veto: 件数に加え、0件時の解釈（veto不在=追加可ではない）を明示する。

## Email Preview Treatment

- txt/htmlのチェックリストへ短縮理由メモを挿入する。
- HTMLは `ul/li` を使い、モバイルでも崩れにくい構造を維持する。
- 「veto該当0件でも、coverage/score再確認を優先」の注意文を固定表示する。

## Safety Boundary

本変更は source-only の表示/文言改善であり、以下は不実施:

- workflow変更
- provider live HTTP / market-data live fetch
- cache write / actual import
- broker API / raw broker export parsing
- env/secret 表示
- dependency / pyproject / Makefile変更
- trading action / order placement / 実メール送信

## Tests

- `tests/test_weekly_candidate_brief_v0.py`
  - 候補0件理由メモ、coverage/score/veto 表示、veto 0件解釈を検証
- `tests/test_weekly_candidate_brief_email.py`
  - txt/html短縮理由メモ、veto 0件時の抑制文言を検証
- focused:
  - `env PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_weekly_candidate_brief_v0.py tests/test_weekly_candidate_brief_email.py`
  - `env PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_weekly_candidate_brief_v0.py tests/test_weekly_candidate_brief_email.py tests/test_target_allocation_gap_calculator_v82.py tests/test_monthly_decision_sheet_v84.py`

## Next Actions

1. v87 PRをCI greenでレビューし、人間承認後にmerge判断
2. scheduled run観測で候補0件時の理由メモ表示を再確認
