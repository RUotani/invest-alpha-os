# Approved execution report — 2026-05-25

## 3行サマリー
- 承認 A/B/C すべて YES に基づき P10 AMD cache write・週次 observation_log 書込・portfolio **25%** を反映。
- tier-1 missing **解消**（AMD 10879 bars）。forward matched は依然 0（fresh-log · docs/161 想定内）。
- Product PR: weekly 書込統計 markdown · evidence manifest 2件。

---

## 承認 A — P10 AMD refresh

| 項目 | 結果 |
| --- | --- |
| CLI | `debug us-provider-cache-preview --symbol AMD --live --write-cache` |
| status | success · cache_write=true |
| bars | 10879 · last_date 2026-05-22 |
| tier1_missing 後 | `[]` |

Evidence: `outputs/evidence/p10_tier1_post_20260525.md`  
Manifest: `reports/2026-05-25/evidence_manifest_p10_amd_refresh_20260525.md`

---

## 承認 B — weekly write

| 項目 | 結果 |
| --- | --- |
| CLI | `weekly-us-observation --write-observation-log --with-peer-sync` |
| observation_log | 58 → **74** lines |
| us_signal_rows | **64** |

Manifest: `reports/2026-05-25/evidence_manifest_weekly_write_20260525.md`

---

## 承認 C — portfolio %

| 項目 | 値 |
| --- | --- |
| rubric tier | **P0**（shadow 0 · P1 N/A） |
| STATE portfolio % | **25%**（docs/154 suggested · human YES 2026-05-25） |

---

## Post-smoke（read-only）

| チェック | 結果 |
| --- | --- |
| ops-smoke --strict | exit 2 · EXPECTED_BLOCKED（tier1_gaps 解消 · repeat/stale 継続） |
| us-forward-returns | matched=0 · insufficient_future_bars=48 |
| observation-health | peer_sync_forward あり · tier1_missing=[] |

---

## Tests

```bash
.venv/bin/python -m pytest -q
```
