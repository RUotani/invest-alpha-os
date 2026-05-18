# R6.15-D — Codex light review prompt (copy-paste pack)

**ステータス**: **ブランチ作業のみ**（**`main` 未反映**）。ブランチ: **`work/r6-15-d-codex-light-review-prompt`**。
**目的**: 下記 **§Codex に貼るプロンプト** を Codex に渡し、**軽量レビュー**（最大 5 指摘）のみ受け取る。**Codex の実行は本リポジトリタスク外**。

---

## レビュー対象（読むファイル）

### R6.15-B（`main` @ `e6e10c5` 付近に反映済み）

| パス | 要点 |
|---|---|
| `scripts/main_gate.sh` | PR 前ローカル gate（**L7–8**: `main` 上では拒否） |
| `Makefile` | `main-gate` target |
| `.pre-commit-config.yaml` | コミット前フック |
| `docs/55_r6_15_b_safety_gate_automation.md` | 設計メモ |

### R6.15-C（**`main` @ `f6250d8`** · PR **#3** merged）

| パス | 要点 |
|---|---|
| `docs/56_r6_15_c_us_cache_population_runbook.md` | US cache population runbook（**docs-only**） |
| `docs/01_development_status.md` | R6.15-C 完了節 |

### 運用コンテキスト

- GitHub **ruleset `main`**: PR 必須 · required check context **`test`**（2026-05-18 に **`tests` から整合**）· strict up-to-date · squash merge。

---

## Codex に貼るプロンプト（以下をそのままコピー）

```markdown
You are reviewing invest-alpha-os safety-gate and US-cache runbook docs only. Do NOT propose new features or expand scope.

## Scope (read these paths)
- R6.15-B on main: scripts/main_gate.sh, Makefile (main-gate), .pre-commit-config.yaml, docs/55_r6_15_b_safety_gate_automation.md
- R6.15-C on main (PR #3 merged): docs/56_r6_15_c_us_cache_population_runbook.md, relevant section of docs/01_development_status.md

## Review questions
1. Is main-gate correctly limited to feature branches (not main)?
2. Does this align with PR-required / ruleset workflow without contradictions?
3. Does anything accidentally permit live HTTP or production cache write?
4. Does the US cache runbook stay docs-only (no hidden scope creep toward R6.16 implementation)?
5. What is missing before starting R6.16 operator-gated batch ingest?

## Constraints for YOUR output
- No new feature proposals
- No scope expansion
- Max 5 findings
- Each finding: severity (HIGH/MEDIUM/LOW) | file | line or section | surgical fix (one sentence)
- No abstract "best practices" essays
- Single markdown block, under 1500 tokens
- At most 3 next actions

## Do not review
- Veto logic, US signals default, portfolio/macro, worktree cleanup, r6-10-g
```

---

## 期待する Codex 出力例（形式のみ）

```markdown
### Findings
1. **MEDIUM** | `scripts/main_gate.sh` | L7–8 | …
...

### Next actions (max 3)
1. …
```

---

## 次候補（人間）

- **R6.15-D**: 本 prompt を Codex に渡して軽量レビュー（**R6.15-E** で結果 docs 化は任意）。
- **R6.16**: runbook §7 の operator-gated batch ingest（**別承認**）。
