# Final Report — Cursor longrun wave 6 (2026-05-26)

<<< COPY FROM HERE >>>

## 結論

**PR #291 merge 済**。US forward P3 の到達経路を **`p3_path_to_usable`** に統合（path A horizon + path B ISO week + gaps + next_steps）。matched **1/10** 変化なし。

確度: **92%**

---

## PR

| PR | 内容 |
| --- | --- |
| #291 | `p3_path_to_usable` + horizon `sessions_until_histogram` |

累計本ロングラン: #284–#291 · docs #286/#290

---

## 監視（1コマンド）

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate forward-p3-status --format markdown
```

JSON: `p3_path_to_usable.dominant_path` · `path_a_horizon_maturation` · `path_b_new_iso_week_writes`

---

## 典型出力（現在）

- `dominant_path`: `iso_week_rollover_then_l1`
- path A: 16 pending horizon rows
- path B: write_now=0 · rollover days_until

---

## Safety

live HTTP / cache write / Gmail: **未実行**

<<< COPY TO HERE >>>
