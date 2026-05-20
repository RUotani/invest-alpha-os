# R7.0-Ops-G2 — recovered true long-run standard profile

**日付**: 2026-05-20 · **性質**: #71 conflict 後の G 層再適用

---

## 1. Cause

- **#70**（native long-run flags）は `main` に merge 済み
- **#71** は #70 を含む stacked PR のため、#70 merge 後に **merge conflict**（`mergeable=false`）
- #71 を merge せず、main 上に **G 差分のみ** を本 PR（G2）で復元

---

## 2. Recovered artifacts

| 項目 | 内容 |
|---|---|
| profiles | `true_longrun_3h` / `true_longrun_6h` |
| code | `apply_profile_longrun_defaults` in `dev_loop.py` |
| script | `scripts/run_true_longrun_3h.sh` |
| docs | 本ファイル + `docs/112` 更新 |

---

## 3. Standard command

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES
bash scripts/run_true_longrun_3h.sh
```

Profile + 明示 CLI flags（caps / min-runtime / heartbeat）で運用忘れを防止。

---

## 4. Prerequisite

- #70 merged（`--min-runtime-minutes` 等は `main` に存在）

---

## 5. Supersedes

- Open **#71** は本 G2 recovery PR で置き換え（自動 close はしない）
