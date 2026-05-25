# Approved execution report — wave3 I/J（2026-05-25）

## 3行サマリー
- **承認 I/J YES** — P10 8銘柄 refresh · weekly 書込（peer_sync 同梱）。
- observation_log **94 → 114**（+20）· peer_sync_forward **6 → 8** matched · US forward **3/10** thin（変わらず）。
- stale_skips=16 は**履歴 log 行**に残存（新 cache は 2026-05-22 まで更新済み）。

---

## 承認 J — P10 refresh

| symbol | bars | last_date | status |
| --- | ---: | --- | --- |
| MSFT | 10125 | 2026-05-22 | success |
| NVDA | 6875 | 2026-05-22 | success |
| AAPL | 10508 | 2026-05-22 | success |
| AMZN | 7295 | 2026-05-22 | success |
| GOOGL | 5475 | 2026-05-22 | success |
| META | 3523 | 2026-05-22 | success |
| AMD | 10879 | 2026-05-22 | success |
| GLDM | 1987 | 2026-05-22 | success |

Evidence: `outputs/evidence/p10_tier1_wave3_ij_20260525.md`（git 外）

---

## 承認 I — weekly write

| 項目 | 結果 |
| --- | --- |
| CLI | `weekly-us-observation --write-observation-log --with-peer-sync` |
| observation_log | **94 → 114** lines |

---

## Post-smoke

| 指標 | 値 |
| --- | --- |
| docs_163_hard_pass | True |
| us_forward matched | 3 (thin) |
| peer_sync_forward matched | **8** (thin · あと2で10) |
| skip_pattern | mixed |
| stale_skips | 16 |

---

## 次

- [ ] 新規承認で weekly 継続（matched 10 目標）
- [ ] 承認 K（P2/P3 後の %）
