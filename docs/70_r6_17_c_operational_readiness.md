# R6.17-C — Operational readiness（opt-in US cache preview）

**ステータス**: **完了 · `main` 反映済み**（PR **#19** · `ee8dda6`）。stale refresh 実施は **[docs/73](./73_r6_17_d_stale_refresh_status.md)**（R6.17-D · operator · cache local only）。

---

## 1. Purpose

- R6.17 **opt-in preview** を実運用に近づけるための readiness 整理
- **default は off のまま**
- **operator opt-in のみ**
- **observation-only** · **trading recommendation ではない**

---

## 2. Current capability（`main`）

| 能力 | 状態 |
|---|---|
| `daily --us-cache-preview` | **実装済み**（PR #16 · `879fe47`） |
| default daily | preview 節 **なし** |
| opt-in daily | preview 節 **あり** |
| live HTTP / cache write | **なし**（preview パス） |
| freshness gate | inventory `freshness_status` · 7 暦日 cutoff |
| stale 行 | note: **`stale — returns not used`** |
| forbidden terms | preview 節内に buy/sell/veto/macro/production 等 **なし**（smoke 済み） |

---

## 3. Current known state（参考 · local gitignored cache）

| 指標 | 値 |
|---|---:|
| total_symbols | 16 |
| ok | 16 |
| missing | 0 |
| invalid / insufficient / stale_unknown | 0 |
| fresh_enough | 13 |
| stale | 3 |
| freshness_unknown | 0 |

**stale symbols（2026-05-20 refresh 前）**: MSFT · GOOGL · GLDM — **R6.17-D 後は stale 0**（[docs/73](./73_r6_17_d_stale_refresh_status.md)）

---

## 4. Operational modes

| Mode | 説明 | 現状 |
|---|---|---|
| 1. Ad-hoc manual opt-in | operator が必要時のみ `--us-cache-preview` | **受理** |
| 2. Scheduled operator opt-in | cron/手動スケジュールで read-only daily | **検討可**（別 runbook 化） |
| 3. Default enablement | daily 既定で preview 節 | **別承認** · [docs/72](./72_r6_17_c_default_enablement_checklist.md) |
| 4. Production integration | decision / signals 接続 | **別フェーズ** · R6.17+ |

---

## 5. Recommended near-term operation

1. **default enable しない**
2. opt-in は **手動または operator トリガーのみ**
3. **stale warnings を隠さない**（MSFT/GOOGL/GLDM）
4. 出力を **売買指示とみなさない**
5. **observation layer** として inventory + preview を併読

---

## 6. 関連

- [docs/69_r6_17_b_opt_in_us_cache_preview_runbook.md](./69_r6_17_b_opt_in_us_cache_preview_runbook.md)
- [docs/71_r6_17_c_stale_refresh_approval_package.md](./71_r6_17_c_stale_refresh_approval_package.md)
- [docs/72_r6_17_c_default_enablement_checklist.md](./72_r6_17_c_default_enablement_checklist.md)
