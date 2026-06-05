# Weekly Artifact Gap Analysis — 2026-06-06

## Summary

- **Gap**: `weekly_candidate_brief.json` が runner で生成されていなかった
- **Fix**: `run_weekly_candidate_brief.sh` に `--format json` 追加（source-only）
- **Residual**: GitHub Actions artifact upload path は workflow 変更が必要（未実施）

## status.json との関係

v104 `status.json` は `reports.json_report` に JSON パスを記録可能。  
修正後の runner は `weekly_candidate_brief.json` を生成し、status に参照を残す。

## CI artifact checklist（v101）

| Artifact | Runner 生成 | CI upload（現状） |
| --- | --- | --- |
| weekly_candidate_brief_v0_1.md | yes | yes |
| weekly_candidate_brief_copy.md | yes | yes |
| weekly_candidate_brief.json | **yes（修正後）** | **no**（workflow 待ち） |
| email preview | yes | yes |
| status.json | yes | yes |

## Next

1. 次回 scheduled run 後、runner ログで JSON 生成を確認
2. workflow upload 拡張は別承認パッケージで検討
