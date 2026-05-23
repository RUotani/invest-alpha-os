# R7.0-Ops-I11 — v3 productive 12h queue runbook

## Queue tiers

| Tier | Count | Purpose |
|---|---:|---|
| primary | 18 | 必須・高価値（docs/tests/operator 境界） |
| reserve | 30 | 時間があれば実行（tests + docs） |
| stretch | 36 | 余裕時 docs-only（`git diff --check`） |

## Caps（初回）

- `max_prs`: 15（レビュー可能範囲）
- `max_tasks`: 72
- `allow_early_completion` + `--completion-notify`
- **not** durability min-runtime 完走目的

## Start（merge 後・main 上）

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES
bash scripts/run_productive_true_longrun_12h_v3.sh
```

## Safety

auto-merge 禁止 · live HTTP / cache write / Gmail / trading 文言禁止。
