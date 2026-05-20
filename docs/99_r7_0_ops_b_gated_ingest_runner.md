# R7.0-Ops-B — Gated ingest runner task foundation

**日付**: 2026-05-20 · **main 起点**: `9fc2f51` · **性質**: gated execution mode + ingest task YAML + checkpoint/resume

---

## 1. Purpose

Ops-A runner を拡張し、J-Quants ingest のような **長時間・小分け・停止条件付き** 処理を task YAML で扱える基盤を追加する。

**本 PR では real live ingest は実行しない**（simulation / mock テスト中心）。

---

## 2. Execution modes

| mode | 説明 |
|---|---|
| `dry_run` | **default** — plan/checkpoint/evidence のみ |
| `execute_readonly` | readonly CLI / discovery のみ |
| `execute_gated` | gated ingest batch（3 ゲート必須） |

CLI:

```bash
alpha-os operator-runner run --dry-run
alpha-os operator-runner run --execute-readonly --task config/tasks/...
alpha-os operator-runner run --execute-gated --task config/tasks/r7_0_jquants_ingest_gated_smoke.yaml
alpha-os operator-runner run --execute-gated --resume-run-dir outputs/operator/runner/.../RUN_ID
```

---

## 3. Gates (`execute_gated`)

| env | 値 |
|---|---|
| `CONFIRM_LIVE_HTTP` | `YES` |
| `CONFIRM_CACHE_WRITE` | `YES` |
| `CONFIRM_OPERATOR_GATED_INGEST` | `YES` |

不足時: 実行せず `blocked` を checkpoint/evidence に記録。

---

## 4. Task YAML

`config/tasks/r7_0_jquants_ingest_gated_smoke.yaml`

- 1 symbol / batch
- delay 120s（task 定義；テストは 0s）
- step kind: `gated_ingest_batch`
- `simulate: true`（Ops-B 標準）

---

## 5. Checkpoint / resume

- `checkpoint.json` — step 状態 + gate_status + counts
- `ingest_progress.json` — completed / blocked / failed symbols + batches
- `--resume-run-dir` で同一 run_dir から未完了 symbol のみ再開

---

## 6. Stop conditions

- HTTP markers: `400`, `429`, `http_status_400`, `http_status_429`
- forbidden output terms（discovery contract 再利用）
- `--live` / `--write-cache` / `--send` in step args

---

## 7. Boundaries

- real live HTTP / cache write なし（simulation executor）
- Gmail / daily default / trading recommendation 変更なし
- `outputs/` 未コミット

---

## 8. Verification

```bash
pytest -q tests/test_operator_runner.py tests/test_operator_runner_gated.py
alpha-os operator-runner run --dry-run --task config/tasks/r7_0_jquants_ingest_gated_smoke.yaml
```
