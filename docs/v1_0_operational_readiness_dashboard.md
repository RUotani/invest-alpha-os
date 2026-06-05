# v1.0 Operational Readiness Dashboard

版: 2026-06-06（07:58 JST 観測反映）  
固定分母: **core 12 + observation 2 + boundary 1 = 15**

## 使い方

毎朝、次を実行して stdout を確認する（副作用なし）:

```bash
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main v1-readiness-check --format markdown
```

`v1_usable_tomorrow: true` なら **fixture/sample ベースの初日運用 OK**。  
observation 2件は v1.0 完全化待ちであり、初日の手動レビューを阻害しない。

## ドメイン別（固定分母）

| Domain | 完了 | 固定 | 進捗 | 意味 |
| --- | ---: | ---: | ---: | --- |
| Core（明日実用） | 12 | 12 | 100% | 週次 Brief・CLI・docs |
| Observation | 0 | 2 | 0% | scheduled run / CI JSON |
| Boundary（意図的 NO-GO） | 1 | 1 | 100% | import・自動売買は対象外 |

## Core チェックリスト（12）

- [x] 候補0件週テンプレ（#487）
- [x] 候補あり週テンプレ（#495）
- [x] `weekly-report-user-summary` CLI
- [x] `weekly-artifact-local-verify` CLI
- [x] `operator-dashboard-summary` CLI
- [x] `progress-dashboard-check` 整合
- [x] project goal 明文化
- [x] operator user guide
- [x] 週次10分フロー
- [x] 明日運用チェックリスト
- [x] one-page summary sample
- [x] monthly decision sheet fixture

## Observation チェックリスト（2）

- [ ] natural scheduled run 観測 — **pending** `OBSERVATION_PENDING_SCHEDULED_RUN_NOT_VISIBLE`（2026-06-06 07:58 JST）
- [ ] CI `weekly_candidate_brief.json` upload（workflow 承認待ち）

初日運用（2026-06-07）は core 12/12 完了のため **observation pending でも開始可**。  
詳細: `reports-private/scheduled_observation/scheduled_run_observation_20260606.md`

## Boundary（1）

- [x] actual import / broker / 自動売買 — **意図的 NO-GO**

## v1.0 と Report MVP の関係

| 指標 | 値 | 備考 |
| --- | ---: | --- |
| v1.0 core | 12/12 | 明日運用の最低ライン |
| Report MVP | 17/20 | `docs/progress_dashboard.md` |
| 加重参考 | 82% | 単一総合%は運用禁止 |

## 関連コマンド

```bash
v1-readiness-check --format markdown
weekly-report-user-summary --format markdown --source composed
weekly-artifact-local-verify --report-date <date> --json-report-optional
operator-dashboard-summary --format markdown
```
