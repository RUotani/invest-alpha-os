# R6.18-B+C — Default enablement readiness checklist (planning)

**日付**: 2026-05-20  
**性質**: **checklist only** · **default は本 PR では有効化しない**

---

## 1. Default Enablement Is Not Approved

```text
R6.18-B+C does not enable default daily/signals US cache preview.
```

B+C planning は **B1 opt-in signals** の設計と、将来の default 判断に必要な **証拠・ゲート**を文書化するのみ。

---

## 2. Preconditions Before Any Default Enablement PR

以下を **すべて** 満たすまで、default enablement PR を起票しない。

| # | Precondition |
|---|---|
| 1 | inventory: **fresh_enough 16 / stale 0**（判断時点） |
| 2 | **2 回以上**の read-only smoke（**異なる営業日または運用日**） |
| 3 | daily default / signals default 挙動が文書化済み |
| 4 | opt-in 出力が安定（列契約・note 契約不変） |
| 5 | forbidden terms **検出なし** |
| 6 | **no live HTTP**（preview パス） |
| 7 | **no cache write**（preview パス） |
| 8 | **no cache JSON commit** |
| 9 | product code の **surprise change なし** |
| 10 | **Codex read-only review** 完了 |
| 11 | default 挙動変更時は **Claude architecture review** |
| 12 | **rollback plan** 文書化 |
| 13 | operator runbook 更新 |
| 14 | **CI pass** |
| 15 | default-off / opt-in テスト完備 |

**追加（B1 実装後）**: `signals --us-cache-preview` opt-in が **2+ smokes** で安定していること。

---

## 3. Decision Matrix

| condition | decision |
|---|---|
| stale > 0 | **do not** enable default |
| freshness_unknown > 0 | **do not** enable default |
| output contract unstable | **do not** enable default |
| forbidden terms appear | **do not** enable default · **stop** implementation |
| B1 opt-in signals stable | **consider** next review（default ではない） |
| 2+ smokes pass | **eligible for default review only**（自動承認ではない） |
| missing / invalid > 0 | **do not** enable default |
| live HTTP in preview path | **do not** enable default · fix first |

---

## 4. Rollback Plan

| 段階 | 手順 |
|---|---|
| default 有効化後の障害 | default フラグ変更を **revert**（1 PR） |
| opt-in 維持 | `--us-cache-preview` は **残す**（operator  escape hatch） |
| output contract 破綻 | preview 節生成を **feature flag off** 相当で無効化 |
| bad cache symbol | ローカル cache を quarantine · **JSON は commit しない** |
| インシデント | docs に記録 · inventory 再確認 |

---

## 5. Required Evidence Table（placeholder）

実施時に operator が埋める。planning 時点では **N/A**。

| evidence | status | date | notes |
|---|---|---|---|
| inventory summary | _pending_ | | fresh_enough / stale counts |
| daily smoke (default) | _pending_ | | no preview section |
| daily smoke (opt-in) | _pending_ | | preview present |
| signals smoke (default) | _pending_ | | B1 後 |
| signals smoke (opt-in) | _pending_ | | B1 後 |
| forbidden terms check | _pending_ | | grep / test |
| urlopen / no-live guard | _pending_ | | test |
| no-cache-write guard | _pending_ | | test |
| CI run | _pending_ | | GitHub Actions |
| Codex review | _pending_ | | `.agent/r6_18_bc_codex_review_prompt.md` |
| Claude arch review | _pending_ | | default 変更時のみ |
| operator decision | _pending_ | | explicit approval |

---

## 6. 関連

- Connection design: [docs/74](./74_r6_18_bc_cache_only_connection_design.md)
- R6.17-C checklist（先行）: [docs/72](./72_r6_17_c_default_enablement_checklist.md)
- Runbook: [docs/69](./69_r6_17_b_opt_in_us_cache_preview_runbook.md)
