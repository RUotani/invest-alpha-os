# Cursor Agent longrun standard adoption

**日付**: 2026-05-24 · **性質**: Agent workflow · Product-adjacent ops

---

## 決定

Cursor Agent のロングラン自律開発は `.agent/cursor_agent_quality_efficiency_longrun_standard.md` を SSoT とする。

## 理由

- 2026-05-24 の ChatGPT レビューで、P10 env preflight・`--strict` reason taxonomy・evidence manifest 等のギャップが明示された。
- 人間は merge / live HTTP / cache write / Gmail / portfolio % 確定のみ担当し、Agent は PR 整理まで自走する。

## 主要ルール（要約）

| 項目 | 方針 |
| --- | --- |
| P10 refresh | 承認後も env preflight · `BLOCKED_ENV_MISSING` で停止可 |
| ops-smoke `--strict` | exit code 単体でなく reason taxonomy |
| observation_log repeat | raw 削除しない · summary feature 化 |
| evidence | git 外 OK · `reports/.../evidence_manifest_*.md` を repo に |
| Merge queue | Agent は `PENDING_CHATGPT` まで · MERGE 判定は ChatGPT |

## 反証

- 標準が厚すぎると Agent が docs 更新に偏る → §5「後回し」で抑制。
- ChatGPT merge 分類がボトルネックになる → merge queue は複数 PR 時のみ必須。

## 関連

- `.agent/cursor_agent_quality_efficiency_longrun_standard.md`
- `AGENTS.md` §3 Cursor
- `.cursor/rules/main.mdc`
