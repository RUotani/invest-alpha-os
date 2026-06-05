# Decision — Ruff Debt Reduction (2026-06-06)

## Summary

| Metric | Value |
| --- | --- |
| before | 44 errors |
| after | **0 errors** |
| auto-fix | 38（`ruff check . --fix`） |
| manual fix | 6（F841 unused variables） |

## Fixed categories

- F401 unused imports（38件、自動修正）
- F841 unused local variables（6件、手動削除/呼び出しのみに変更）

## Skipped categories

- なし（全件安全範囲で解消）

## Tests

- full pytest: CI で確認（#475 予定）

## Safety

- ビジネスロジック変更なし（未使用変数削除・import整理のみ）
- workflow / pyproject / Makefile: 未変更
