# R7.0-Ops-I2 — productive 8h fail-fast preflight

**日付**: 2026-05-21 · **性質**: pytest/PATH 不足の即時検出と operator alert

---

## 1. Root cause (observed)

- `FileNotFoundError: pytest` during productive 8h run
- child subprocess did not resolve `pytest` on PATH
- `.venv/bin/pytest` existed but was not exported before `dev-loop`

---

## 2. Fix

`scripts/run_productive_true_longrun_8h.sh` now:

1. `export PATH="$REPO_ROOT/.venv/bin:$PATH"`
2. Preflight: gates, clean tree, `.venv/bin/python`, pytest (`pytest` or `python -m pytest`), queue, profile YAML, `gh`
3. On preflight fail: `PRODUCTIVE-LONGRUN-8H PREFLIGHT FAILED: <reason>` + next action → **exit immediately** (no 8h start)
4. On runtime fail: `PRODUCTIVE-LONGRUN-8H FAILED`, log path, evidence path, tail 80 lines
5. On success: `PRODUCTIVE-LONGRUN-8H SUCCEEDED`, stop_reason, evidence, open PRs
6. Optional silent macOS notification at end only (no sound)

---

## 3. Operator reactions

| Signal | Meaning | Action |
|---|---|---|
| `PREFLIGHT FAILED` | env/config | fix venv/pytest/gates; **do not wait** |
| `FAILED: dev_loop_rc=1` | runtime error | read log + evidence |
| heartbeat lines | waiting for min_runtime | **let it continue** |
| `stop_reason=min_runtime reached: 480` | success | review PRs; merge by human |

---

## 4. Command

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES
bash scripts/run_productive_true_longrun_8h.sh
```

Preflight only (manual):

```bash
.venv/bin/python -m pytest --version
gh --version
git status --short
```
