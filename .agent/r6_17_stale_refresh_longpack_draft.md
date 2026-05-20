# DRAFT — R6.17 stale refresh (MSFT / GOOGL / GLDM)

```text
DO NOT EXECUTE THIS DRAFT WITHOUT SEPARATE USER APPROVAL.
```

## 実行場所

Cursor右側Agent（右ペイン）。ターミナル用ではない。

## 目的

- **MSFT** · **GOOGL** · **GLDM** の cache を gated ingest で更新
- inventory: **fresh_enough 13 → 16** · **stale 3 → 0**
- **default enablement なし** · **code 変更なし**

## 現在状態

- `origin/main`: （実行時に記入）
- Approval: [docs/71_r6_17_c_stale_refresh_approval_package.md](../docs/71_r6_17_c_stale_refresh_approval_package.md)
- Runbook: [docs/69_r6_17_b_opt_in_us_cache_preview_runbook.md](../docs/69_r6_17_b_opt_in_us_cache_preview_runbook.md)

## 必須承認

| Gate | Env / action |
|---|---|
| Live HTTP | **`CONFIRM_US_LIVE_HTTP=YES`** |
| Cache write | **`CONFIRM_US_CACHE_WRITE=YES`** |
| Symbols | **MSFT, GOOGL, GLDM only** |
| User | ChatGPT / operator **explicit go** |

**禁止**: `.env` / API key 値の出力 · cache JSON commit

## Sound policy

`.agent/standard_clauses.md` — **no intermediate sounds** · completion sound only at end.

## Stages（実行時）

1. Preflight: read-only inventory（baseline 記録）
2. Per symbol（MSFT → GOOGL → GLDM）:
   - live **no-write** preview → `preview_ok`
   - gated **write** → success
3. After: read-only inventory（fresh_enough / stale 確認）
4. Optional: `daily --us-cache-preview` read-only smoke
5. Final report（単一 Markdown コードブロック）

## 禁止

- main push · force push · branch/worktree 削除
- default daily 変更 · workflow/Makefile/pyproject
- 対象外 symbol · batch 無断拡大
- Veto / portfolio / macro

## Final report

`.agent/report_template.md` + inventory before/after 要約（full log 禁止）
