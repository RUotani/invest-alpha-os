# DRAFT — R6.18-I later-date signals preview smoke (do not execute)

```text
DO NOT ENABLE DEFAULT. READ-ONLY LATER-DATE SMOKE ONLY.
```

## 前提

- R6.18-H: default **blocked** · 同一暦日 2 smoke は **calendar-day gate 未充足**
- 本タスクは **暦日が R6.18-G #1/#2（2026-05-20）より後**の日に実行すること

## 目的

- read-only smoke（default + opt-in）を 1 回記録
- [docs/78](../docs/78_r6_18_f_signals_us_cache_preview_operational_evidence.md) §4 に **3 行目**を追加
- **docs-only PR** · **no default enablement**

## 手順（要約）

1. `git pull --ff-only origin main` · clean tree
2. cache hash before/after（変更なし）
3. `signals --dry-run` · `signals --dry-run --us-cache-preview`
4. preview blob forbidden terms · stale/fresh_enough 要約
5. `pytest -q tests/test_us_cache_preview_opt_in.py`
6. docs/78 1 行 · PR · CI · merge（`--delete-branch=false`）

## 禁止

- product / workflow / Makefile / pyproject 変更
- live HTTP · cache write · cache JSON commit
- default enablement · main direct push · force push

## 完了後

- R6.18-J default-readiness 再レビュー（別 Longpack · 別承認）
