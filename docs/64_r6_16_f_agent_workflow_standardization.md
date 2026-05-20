# R6.16-F — Agent workflow and reporting standardization

**ステータス**: **ブランチ作業のみ**（**`main` 未反映**）。ブランチ: **`work/r6-16-f-agent-workflow-standardization`**。

## Why this PR exists

Operator loops fragmented across ChatGPT paste steps, Cursor implementation, Codex review, and Claude architecture checks. This PR adds **shared templates** so each role uses the same safety clauses, report shape, and Longpack skeleton—without changing product code paths.

## Problem

- Many short human copy-paste commands per task
- Inconsistent final reports (full logs, secrets risk)
- Unclear stop/merge rules across agents

## New policy

- **Minimum human paste / maximum agent autonomy**
- **Longpacks** for Cursor Agent (and similar) multi-stage runs
- **Single Markdown code block** final reports with State Capsule
- **No** full diff / full file / full pytest or CI logs in chat

## Role split

| Role | Responsibility |
|---|---|
| **ChatGPT** | Strategy, Longpack authoring, merge approval, high-risk gates, handoff files |
| **Cursor Agent** | Implementation, docs, tests, PR create, CI watch, failure classification, final report |
| **Codex** | Read-only PR review, contract/tests/boundary audit (`.agent/codex_review_template.md`) |
| **Claude Code** | High-risk architecture review before defaults / live HTTP / cache write (`.agent/claude_arch_review_template.md`) |

## Risk-based workflow

- **Low**: docs, templates, read-only smoke → batch in one Longpack
- **Medium**: CLI, inventory extension, previews → implement + Codex review
- **High**: live HTTP, cache write, daily/signals defaults, Veto/portfolio/macro → Claude review + human approval

## Artifacts added

```text
.agent/standard_clauses.md
.agent/report_template.md
.agent/safety_rules.md
.agent/cursor_longpack_template.md
.agent/codex_review_template.md
.agent/claude_arch_review_template.md
CLAUDE.md
```

## Non-goals (this PR)

- No R6.17 daily/signals connection
- No live HTTP or cache write implementation
- No workflow / Makefile / `pyproject.toml` changes
- No daily/signals default changes

## Relation to R6.17+

R6.16-F is the **operating substrate** before R6.17 and later phases. Product work still requires phase-specific Longpacks and approvals.

## How to write future Longpacks

1. Start from `.agent/cursor_longpack_template.md`
2. Attach `.agent/standard_clauses.md` prohibitions
3. End with `.agent/report_template.md`
4. Reference `docs/01` for what is already on `main`
