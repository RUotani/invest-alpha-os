# Longrun 自律開発 — 運用契約（2026-05-25）

## 定義（ユーザー合意）

**ロングラン** = 人間が PC 操作・ターミナル実行・コマンドコピペを**一切不要**な開発方式。

| 担当 | 内容 |
| --- | --- |
| **Agent** | 設計・実装・テスト・PR 作成・squash merge・read-only 検証・`reports/` 更新 |
| **人間** | PR merge 判断（任意）· **チャットでの gated 承認のみ**（live HTTP / cache write / weekly 書込 / Gmail / portfolio %） |

## gated 操作（チャット YES のみ · 人間ターミナル不要）

- P10 `debug us-provider-cache-preview --live --write-cache`
- `weekly-us-observation --write-observation-log`
- `./scripts/run_daily_gmail_report.sh --send`
- `config/portfolio_observation_acceptance.yaml` の % 更新

承認後は **Agent がローカルで実行**し、証跡を `reports/` と `outputs/evidence/`（git 外）に残す。

## Agent が止まらず進めるもの（承認不要）

- `signals/` / `portfolio/` / `reports/` の read-only Product コード
- `validate *` / `snapshot *`（HTTP・outputs 書込なし）
- テスト · CI · PR 連続 merge

## キュー（gated · チャット待ち）

wave4: **M** weekly · **N** portfolio % — [approval_requests_wave4_20260525.md](./approval_requests_wave4_20260525.md)

※ 承認はこのチャットに `承認 M: YES` 形式で返すだけでよい。ターミナル操作は不要。
