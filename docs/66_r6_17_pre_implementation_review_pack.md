# R6.17 — Pre-implementation review pack

**ステータス**: **ブランチ作業のみ**（review prompts · **実装なし**）。
**ブランチ**: **`work/r6-17-pre-implementation-review-pack`**

---

## 0. R6.17 implementation blockers (resolved in implementation PR)

| Blocker | Resolution |
|---|---|
| `return_1d` missing from metrics | Add to `compute_us_daily_bars_basic_metrics` with horizons `[1, 5, 20]` |
| `volume_status` undefined | Fixed contract below (prior-25 average, exclude latest bar) |
| Freshness / stale scoring | Preview builder uses `freshness_status`; stale rows get note; **no aggregate score** in R6.17 v1 |

### Fixed `volume_status` contract

```text
volume_ratio = last_volume / average(prior_25_volumes)

volume_status:
- "high" if volume_ratio >= 2.0
- "low" if volume_ratio < 0.5
- "normal" otherwise
- "unknown" if insufficient prior bars (<5), missing volume, zero/invalid average
```

Prior volumes exclude the latest bar; if fewer than 25 prior bars but ≥5, average available prior bars.

### Fixed `return_1d`

Same pattern as `return_5d` / `return_20d`; `None` if insufficient bars.

### Freshness gate (preview)

- Stale rows may appear if **clearly marked**; note: `stale — returns not used`
- `freshness_unknown`: `freshness unknown — returns not used`
- **Default daily** must **not** include US cache preview section (CLI opt-in only)

---

## 1. Why review before implementation

R6.17 touches **daily report output surface** (opt-in only) near **signals** boundaries. A planning mistake could leak into defaults, stale handling, or production gates. This pack separates **review** from **implementation**.

---

## 2. What PR #14 merged (`33f6f29`)

- [docs/65_r6_17_opt_in_us_cache_preview_plan.md](./65_r6_17_opt_in_us_cache_preview_plan.md) — scope, §5 policies (stale, benchmarks, columns)
- [docs/01_development_status.md](./01_development_status.md) — R6.17 planning entry
- [.agent/r6_17_cursor_longpack_draft.md](../.agent/r6_17_cursor_longpack_draft.md) — **non-executable** implementation Longpack draft

---

## 3. What must be reviewed before implementation

| Reviewer | Artifact | Focus |
|---|---|---|
| **Codex** | [.agent/r6_17_codex_review_prompt.md](../.agent/r6_17_codex_review_prompt.md) | scope, tests, contract gaps, default forbidden |
| **Claude Code** | [.agent/r6_17_claude_arch_review_prompt.md](../.agent/r6_17_claude_arch_review_prompt.md) | layer boundaries, stale policy, rollback, merge blockers |

---

## 4. Codex usage

- **Read-only** on planning + later implementation PR
- Summarize gaps; no full diffs/logs
- After code PR: contract break · opt-in-only golden · env isolation

---

## 5. Claude Code usage

- Run **before** approving implementation Longpack execution
- Confirm **daily/signals default unchanged**
- Sign off **medium-risk opt-in** or list conditions

---

## 6. When to run implementation Longpack

Proceed only if:

1. Codex planning review: **approve** or minor doc fixes merged
2. Claude arch review: **proceed-with-conditions** with conditions tracked
3. ChatGPT/user explicit **implementation approval**
4. This review pack PR merged (or acknowledged)

---

## 7. Implementation approval checklist

- [ ] docs/65 §5 understood (stale mark + warn; no scoring input)
- [ ] Opt-in flag name and default **off** documented
- [ ] Default daily golden **unchanged**
- [ ] No live HTTP / cache write in implementation PR
- [ ] No Veto / portfolio / macro in implementation PR
- [ ] Rollback = disable flag
- [ ] CI green on implementation PR
- [ ] Codex PR review on implementation PR
- [ ] Human merge approval

---

## 8. Related

- [docs/65_r6_17_opt_in_us_cache_preview_plan.md](./65_r6_17_opt_in_us_cache_preview_plan.md)
- `.agent/r6_17_cursor_longpack_draft.md` (execute only after checklist)
