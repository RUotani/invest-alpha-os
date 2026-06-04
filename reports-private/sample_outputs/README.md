# Sample Outputs（fixture-only）

観測・レビュー用の**サニタイズ済み fixture** 出力です。売買指示ではありません。実データの正確性・鮮度は主張しません。

| ファイル | 由来 |
| --- | --- |
| `weekly_candidate_brief_sample.md` | `weekly_candidate_brief_v0` copy-ready（候補0件 fixture） |
| `monthly_decision_sheet_sample.md` | `monthly_decision_sheet_v84` |
| `portfolio_data_quality_review_sample.md` | `portfolio_data_quality_review_v109` |
| `raw_input_quarantine_review_sample.md` | `raw_input_quarantine_v110` safe fixture |
| `portfolio_quarantine_cross_review_sample.md` | `raw_input_quarantine_review_v111` |
| `operator_dashboard_sample.md` | 上記 + progress dashboard 要約 |

再生成（source-only）:

```bash
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main raw-input-quarantine-review --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main portfolio-quarantine-cross-review --format markdown
```
