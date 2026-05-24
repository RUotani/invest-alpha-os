# Product ロングラン Handoff — 2026-05-24（更新）

> post #241 · Cursor 承認 A → merge · P10 preflight 再実行

---

## 0. 現在状態

| 項目 | 値 |
| --- | --- |
| **origin/main** | `766eb8c` |
| **open PR** | STATE sync 待ち（post #241） |
| **テスト** | **1052 passed** |
| **observation_log** | **58行**（US 48 + peer_sync 10） |
| **tier-1 missing** | **AMD**（`STOOQ_APIKEY` 未設定） |
| **ops-smoke strict** | taxonomy **EXPECTED_BLOCKED**（repeat + stale · 想定内） |

---

## 0.1 Merge 運用（2026-05-24 確定）

1. Agent が **Cursor 承認依頼**（AskQuestion または明示メッセージ）を人間へ出す
2. 人間が **A（承認）** 等で応答
3. **Cursor Agent** が `gh pr merge --squash` を実行
4. ChatGPT merge queue は記録用（Agent は `PENDING_CHATGPT` のみ付与 · 人間承認後 merge）

---

## 1. 人間承認結果（2026-05-24）

| 項目 | 承認 | 結果 |
| --- | --- | --- |
| 週次 `--write-observation-log` | **yes** | 実行済 |
| P10 AMD refresh | **yes** | **ブロック** · `STOOQ_APIKEY` unset |
| portfolio STATE % | **keep** | `[要確認]%` 維持 |
| #241 merge | **A（Cursor）** | **merged** @ `766eb8c` |

---

## 2. #241 マージ内容

- ops-smoke `strict_taxonomy`
- `log evidence-manifest`
- observation `repeat_summary`
- portfolio readiness labels
- docs/123 · 124 DEPRECATED → docs/81

---

## 3. P10 evidence（git 外）

| ファイル | 内容 |
| --- | --- |
| `outputs/evidence/p10_tier1_amd_refresh_20260524.md` | 初回 refresh 失敗 |
| `outputs/evidence/p10_tier1_pre_20260524.md` | post #241 preflight（STOOQ unset） |

---

## 4. 参照

- Weekly: `docs/160`
- P10: `docs/162` · post: `docs/163`
- Gmail: `docs/81`
- Longrun standard: `.agent/cursor_agent_quality_efficiency_longrun_standard.md`

---

*最終更新: 2026-05-24 · post #241 merge + P10 preflight*
