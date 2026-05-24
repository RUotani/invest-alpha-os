<<< COPY FROM HERE >>>
# Merge Queue — post-rebase 2026-05-24

**Cursor Agent executed ChatGPT REBASE_FIRST for #219–#221.**  
**#218 merged** @ `91da271`.

| PR | Title | Base (now) | CI | Recommendation (ChatGPT) | Agent status |
|---:|---|---|---|---|---|
| #218 | ops smoke + peer_sync log | main | — | MERGE | **MERGED** @ 91da271 |
| #219 | observation-health (Wave B) | **main** (rebased) | re-run pending | MERGE | **ready for human merge** |
| #220 | portfolio exposure (Wave C) | #219 branch (stacked) | re-run pending | REBASE_FIRST → merge after #219 | wait for #219 merge, then rebase to main |
| #221 | P10 + protocol docs | #220 branch (stacked) | re-run pending | REBASE_FIRST / REVIEW | wait for #220 |

## Human merge order (unchanged)

1. ~~#218~~ done
2. **Merge #219** (rebased onto main, 1 commit `be89bee`)
3. Rebase #220 onto `main` → merge
4. Rebase #221 onto `main` → merge (review `.agent/` + `reports/`)

## Tests (Agent)

```bash
.venv/bin/python -m pytest -q  # 1006 passed on rebased #219/#220/#221 stack
```

## Not executed

- `--write-observation-log`, P10 live refresh, Gmail

<<< COPY TO HERE >>>
