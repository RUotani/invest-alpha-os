# R7.0-Ops-A — Autonomous Local Operator Runner (foundation)

**日付**: 2026-05-20 · **main 起点**: `2a36e1b` · **性質**: dry-run runner + policy/task YAML + tests

---

## 1. Purpose

人間の手動コマンド貼り付けから、**policy / task YAML / checkpoint / evidence** で安全を担保するローカル runner 基盤へ移行する第一歩。

本フェーズは **大量 live ingest ではなく** 次を実装する。

- safety policy YAML の読み込み
- task YAML の読み込み
- **dry-run デフォルト**（ステップは `planned` のみ）
- `--execute-readonly` で readonly ステップのみ実行
- checkpoint + evidence summary（`outputs/operator/runner/` · 未コミット）
- live HTTP / cache write は env ゲートなしで拒否
- 禁止 CLI フラグ・禁止出力語・HTTP 400/429 で停止

---

## 2. Artifacts

| パス | 役割 |
|---|---|
| `config/operator_runner_policy.yaml` | 停止条件・ゲート・禁止フラグ |
| `config/tasks/r7_0_discovery_readonly_smoke.yaml` | サンプル readonly タスク |
| `src/invis_alpha_os/operator/` | runner 実装 |
| CLI `operator-runner run` | Typer サブコマンド |

---

## 3. CLI usage

```bash
# Dry-run (default) — plan only, writes checkpoint under outputs/
alpha-os operator-runner run --dry-run

# Read-only execute — runs discover-jp/us + cross-market merge (needs local cache)
alpha-os operator-runner run --execute-readonly \
  --task config/tasks/r7_0_discovery_readonly_smoke.yaml
```

出力先: `outputs/operator/runner/<task_id>/<run_id>/`

- `checkpoint.json`
- `evidence_summary.json` · `evidence_summary.md`
- 実行時のみ step artifacts（例 `discover_jp.json`）

---

## 4. Safety gates

| 条件 | 動作 |
|---|---|
| `--live` / `--write-cache` / `--send` in step args | **即停止** |
| `risk_class: live_http` / `cache_write` step | **即停止**（MVP 未対応） |
| `CONFIRM_LIVE_HTTP=YES` なし | live 系は実行不可 |
| stdout に 400 / 429 | **停止** |
| discovery forbidden terms | **停止** |
| default | dry-run |

---

## 5. Task step kinds (MVP)

| kind | 説明 |
|---|---|
| `cli` | `python -m invis_alpha_os.cli.main <command> ...` |
| `merge_discovery_json` | `merge_cross_market_json_payloads`（2 inputs） |

---

## 6. Boundaries (not in Ops-A)

- Gmail send / daily default 変更なし
- portfolio / macro / Veto 接続なし
- operator-runner からの cache write / live HTTP タスクは次フェーズ
- `outputs/` · cache JSON は **commit しない**

---

## 7. Verification

```bash
pytest -q tests/test_operator_runner.py
alpha-os operator-runner run --dry-run
```

---

## 8. Next (Ops-B+)

- task YAML for gated J-Quants ingest（1 symbol / batch + delay）
- git dirty path stop（allowlist 外変更）
- Gmail 統合節への `common_candidates` 要約
