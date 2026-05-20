# R7.0-Ops-D2 — PR loop CI read-only integration

**日付**: 2026-05-20 · **main 起点**: `6e3cbad` · **性質**: `pr-loop` の CI read-only 監視追加

---

## 1. Purpose

Ops-D の `operator-runner pr-loop` に optional CI 確認を追加し、PR 作成前後の状態を evidence に残す。

- `--check-ci` が明示された場合のみ実行
- 既存 PR (`--pr-number`) または同一 run で作成した PR を対象
- **自動 merge は禁止のまま**

---

## 2. Behavior

| 条件 | 動作 |
|---|---|
| default (`--check-ci` なし) | 従来挙動維持（CIチェックなし） |
| `--check-ci` + PR番号あり | `gh pr checks <num>` 実行（read-only） |
| `--check-ci` + PR番号なし + createなし | blocked（draft_only） |
| CI `success` | 継続 / completed |
| CI `pending`/`failing`/`cancelled`/`unknown` | stopped + evidence へ理由記録 |

---

## 3. Safety

- 許可: `gh pr checks`（read-only）
- 禁止: `gh pr merge`, `gh pr close`, force push, branch削除
- `assert_gh_command_allowed` で merge/close 系を拒否

---

## 4. Evidence

`outputs/operator/pr_loop/<run_id>/evidence_summary.json` に以下を記録:

- `ci_status`: success / pending / failing / cancelled / unknown
- `ci_detail`: checks 出力の要約
- `status`, `stop_reason`
- `forbidden_auto_merge: true`

---

## 5. Tests

- `tests/test_operator_pr_loop.py`
  - default で CI check 未実行
  - `--check-ci` の argv と read-only 経路
  - success / pending の分岐
  - PR番号なし時 blocked
  - merge/close 禁止

---

## 6. Not done

- `gh run list` の追加統合（任意）
- CI再試行ロジックや待機ループ
- 自動 merge（禁止）

