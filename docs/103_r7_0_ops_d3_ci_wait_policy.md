# R7.0-Ops-D3 — PR loop CI wait policy

**日付**: 2026-05-20 · **main 起点**: `2572f16` · **性質**: `pr-loop` の CI 待機ポリシー追加

---

## 1. Purpose

Ops-D2 の `--check-ci`（単発スナップショット）に加え、`gh run list` を read-only でポーリングし、CI 完了まで待機する optional モードを追加する。

- default は待機なし（従来挙動）
- **自動 merge は禁止のまま**

---

## 2. CLI

| フラグ | default | 説明 |
|---|---|---|
| `--wait-ci` | off | `gh run list --branch <branch>` をポーリング |
| `--ci-timeout-seconds` | 600 | 最大待機秒数 |
| `--ci-poll-seconds` | 30 | ポーリング間隔 |

`--check-ci` との併用: wait が success の後に checks スナップショットを実行可能。wait が stopped の場合は checks をスキップ。

---

## 3. Behavior

| 条件 | 動作 |
|---|---|
| default (`--wait-ci` なし) | CI 待機なし |
| `--wait-ci` | branch 上の run をポーリング |
| 全 run `success` | completed |
| `failure` / `timed_out` | stopped · `ci_wait_status=failing` |
| `cancelled` | stopped · `ci_wait_status=cancelled` |
| タイムアウト | stopped · `ci_wait_status=timeout` |

---

## 4. Safety

- 許可: `gh run list`（read-only）、既存の `gh pr checks`
- 禁止: `gh pr merge`, `gh pr close`, auto-merge
- mock subprocess テストのみ（CI 実ネットワーク不要）

---

## 5. Evidence

`outputs/operator/pr_loop/<run_id>/evidence_summary.json` に追加:

- `ci_wait_status`: success / pending / failing / cancelled / timeout / unknown
- `ci_wait_detail`: 要約（poll 回数・timeout 等）
- `ci_wait_poll_count`: ポーリング回数

---

## 6. Tests

- `tests/test_operator_pr_loop.py`
  - default で wait 未実行
  - success / pending→success / failure / cancelled / timeout
  - `--wait-ci` + `--check-ci` 併用

---

## 7. Not done

- 自動 merge（禁止）
- CI 再試行・再実行
- overnight autonomous runner（Ops-E）
