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
| `chatgpt_one_page_summary_sample.md` | 週次/品質/quarantine を1画面要約（ChatGPT貼付用） |
| `cursor_auto_24h_final_summary.md` | 24h Serial Marathon 最終要約 |
| `sample_outputs_review_for_user.md` | ユーザー向けサンプルレビュー要約 |
| `main_development_24h_continuation_summary.md` | Post #474 本開発24h継続サマリ |

各 `.md` 先頭に統一 disclaimer（blockquote）を付与しています。

再生成手順の詳細: `docs/sample_output_regeneration.md`

```bash
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main sample-output-pack --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main portfolio-data-quality-review --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main raw-input-quarantine-review --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main portfolio-quarantine-cross-review --format markdown
```
