# R6.18-H — Default-readiness review package（planning）

**日付**: 2026-05-20 · **main 起点**: `318a7d9`  
**性質**: **review only** · **default enablement 実装なし**

---

## 1. Purpose

- R6.18-H は **default-readiness レビューパッケージ**である
- **daily / signals の default US cache preview は有効化しない**
- R6.18-G の smoke 証拠が default 議論に十分かを評価する
- **同一暦日 2 件**の evidence 問題を明示する

---

## 2. Current Evidence

| 項目 | 内容 |
|---|---|
| Smoke #1 | PR **#25** · main `cd86396` · 2026-05-20 |
| Smoke #2 | PR **#26** · main `318a7d9` · 2026-05-20（別 operator セッション / #2 Longpack） |
| Default excludes preview | **pass**（両回） |
| Opt-in includes preview | **pass**（status ok · **16** rows） |
| stale / fresh_enough | **0** / **16**（両回） |
| live HTTP / cache write | **なし** |
| cache JSON commit | **なし** |
| Forbidden terms（preview） | **なし** |
| Tests | `test_us_cache_preview_opt_in.py` **12 passed** |

詳細行: [docs/78](./78_r6_18_f_signals_us_cache_preview_operational_evidence.md) §4。

---

## 3. Evidence Gate Interpretation

```text
R6.18-G has 2 completed smoke records.
However, the earlier readiness language used “2+ separate operational-day” records.
Because both records are on the same calendar date, R6.18-H classifies the current evidence as:
  - sufficient for opt-in operational confidence
  - not yet sufficient for default enablement approval
unless the operator explicitly accepts same-day separate sessions as satisfying the gate.
```

**推奨（安全側）**: 同一暦日 2 セッションは **opt-in 運用の信頼**には足りるが、**default 承認には不足** — **後日の #3 smoke** を要求する。

同一暦日をゲート充足とみなす場合は、operator が **別途明示ポリシー**として文書化すること（本 doc では採用しない）。

---

## 4. Recommendation

```text
Do not enable default yet.
Require one additional read-only smoke record on a later calendar date before any default enablement implementation PR.
```

**次タスク名**: **R6.18-I** — third / later-date signals preview smoke evidence

---

## 5. Default-Readiness Checklist Status

| gate | current status | decision |
|---|---|---|
| stale 0 / fresh_enough 16 | pass | keep monitoring |
| signals default excludes preview | pass | OK |
| opt-in preview includes 16 rows | pass | OK |
| no live HTTP/cache write | pass | OK |
| no cache JSON commit | pass | OK |
| forbidden terms absent in preview | pass | OK |
| tests pass | pass | OK |
| 2+ smoke records | pass as **sessions** | calendar-day caveat |
| 2+ separate operational-day records | **not clearly satisfied** | **require #3** |
| Codex review for R6.18-F | optional / not run | optional |
| Claude architecture review for default change | not run | **required before default implementation** |
| rollback plan | [docs/75](./75_r6_18_bc_default_enablement_readiness_checklist.md) | verify before default PR |
| operator approval | not granted | **required** |

---

## 6. R6.18-H Decision

```text
R6.18-H decision: default enablement remains blocked.
R6.18-H authorizes only the next evidence task, R6.18-I, to collect a later-date read-only smoke record.
```

---

## 7. R6.18-I Scope

R6.18-I は:

- read-only `signals --dry-run`（default · opt-in）
- live HTTP / cache write なし · cache JSON 不変
- preview 節/blob の forbidden terms なし
- stale 0 / fresh_enough 16（観測時）
- `pytest -q tests/test_us_cache_preview_opt_in.py`
- **docs/78 §4 に 3 行目**（**後日暦日**）を 1 行追加
- **docs-only PR** · **default 有効化なし**

Draft: [.agent/r6_18_i_later_date_signals_preview_smoke_evidence_longpack_draft.md](../.agent/r6_18_i_later_date_signals_preview_smoke_evidence_longpack_draft.md)

---

## 8. What Still Cannot Be Done

- auto default enablement
- buy/sell/recommendation
- portfolio / macro / Veto 接続（preview）
- scoring / ranking
- live ingest / cache write 自動化
- cache JSON commit

---

## 9. Future Path

R6.18-I 完了後:

- **R6.18-J**: 3 evidence 行を前提とした default-readiness 再レビュー
- default 実装を望む場合:
  - Codex read-only review
  - **Claude architecture review**（default 挙動変更）
  - **別 Longpack** で default enablement implementation
  - rollback 計画の再確認

---

## 10. 関連

- Evidence: [docs/78](./78_r6_18_f_signals_us_cache_preview_operational_evidence.md)
- Checklist: [docs/75](./75_r6_18_bc_default_enablement_readiness_checklist.md)
- Design: [docs/74](./74_r6_18_bc_cache_only_connection_design.md)
