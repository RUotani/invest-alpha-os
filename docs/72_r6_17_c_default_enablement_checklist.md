# R6.17-C — Default enablement checklist（preview on daily default）

**ステータス**: **未承認** · **default は現状 off**。

---

## 1. Purpose

- `daily --us-cache-preview` を **default daily** に載せる前の条件を固定する
- **本 checklist 完了 ≠ default 有効化**

---

## 2. Minimum gates（すべて満たすまで default 禁止）

| # | Gate |
|---|---|
| 1 | **`stale_count = 0`**、または stale 残存を **運用方針として文書化・承認** |
| 2 | default-path **golden** を意図的に更新（opt-in 専用 golden と分離） |
| 3 | [docs/69](./69_r6_17_b_opt_in_us_cache_preview_runbook.md) operator 受理 |
| 4 | default path に **live HTTP / cache write なし** |
| 5 | preview に **trading recommendation なし** |
| 6 | **Veto / portfolio / macro** 非接続 |
| 7 | 実装 PR 後 **Codex review** |
| 8 | **ChatGPT / ユーザー明示承認** |
| 9 | **rollback 文書化**（フラグ off = 現状復帰） |

---

## 3. Out of scope（default enable でも含めない）

- automatic cache refresh
- production provider fallback
- portfolio allocation
- macro regime **最終判断**
- Veto integration
- buy/sell automation

---

## 4. Proposed future path

1. **Stale refresh**（[docs/71](./71_r6_17_c_stale_refresh_approval_package.md)）
2. Smoke: **fresh_enough 16 / stale 0**（read-only inventory + opt-in daily）
3. **Scheduled opt-in** runbook（mode 2）
4. **Default enablement proposal**（本 checklist レビュー）
5. Codex / Claude arch review
6. **Implementation PR**（承認後のみ）

---

## 5. 関連

- [docs/70_r6_17_c_operational_readiness.md](./70_r6_17_c_operational_readiness.md)
- [docs/65_r6_17_opt_in_us_cache_preview_plan.md](./65_r6_17_opt_in_us_cache_preview_plan.md)
