# R7.0-Ops-C — Gated J-Quants ingest wiring

**日付**: 2026-05-20 · **main 起点**: `e23d9fb` · **性質**: CLI command wiring + planned templates（real live ingest なし）

---

## 1. Purpose

Ops-B の `gated_ingest_batch` を既存 **`debug jquants-watchlist-bars-cache`** CLI に配線する。

- dry-run: command template を evidence に記録（`--live` なし）
- execute-gated + simulate=false: 3ゲート成立時のみ `--live --write-cache` を付与して subprocess
- **CI/テスト**: mock subprocess のみ · real HTTP/cache write なし

---

## 2. Task YAML extension

`ingest_wiring` block:

```yaml
ingest_wiring:
  cli_subcommand: jquants-watchlist-bars-cache
  from_date: "2025-06-01"
  to_date: "2026-02-17"
```

1 symbol / batch: `--codes SYMBOL --limit 1`

---

## 3. Modules

| ファイル | 役割 |
|---|---|
| `operator/jquants_ingest_wiring.py` | argv 構築 · subprocess executor factory |
| `operator/task_spec.py` | `ingest_wiring` 読み込み |
| `operator/runner.py` | dry-run planned commands · wired executor |

---

## 4. Safety (unchanged)

- dry-run default
- execute-readonly は gated task 拒否
- execute-gated は 3× `CONFIRM_*=YES`
- 400/429 marker stop + resume skip
- outputs/cache JSON/secrets 未コミット

---

## 5. Verification

```bash
pytest -q tests/test_operator_runner_jquants_wiring.py tests/test_operator_runner_gated.py
alpha-os operator-runner run --dry-run --task config/tasks/r7_0_jquants_ingest_gated_smoke.yaml
```

---

## 6. Human live ingest (out of scope)

実データ ingest はオペレータが env ゲートを明示設定した上で  
`--execute-gated` + task `simulate: false` を **ローカル手動**で実行。本 PR では行わない。
