# DRAFT — R6.17 opt-in US cache-only preview (do not execute)

> **Status**: planning draft only. **Do not run** until ChatGPT/user approves a separate implementation Longpack.

## 実行場所

Cursor右側Agent（右ペイン）。ターミナル用ではない。

## 目的

- US cache-only データの **opt-in** markdown プレビュー節を追加する
- **daily / signals default は変更しない**
- freshness gate と output contract をテストで固定する

## 現在状態

- `origin/main`: （実装開始時に記入）
- US cache: ok 16 / missing 0（local gitignored）
- Freshness: R6.16-E on main（7 暦日 cutoff）
- 設計: [docs/65_r6_17_opt_in_us_cache_preview_plan.md](../docs/65_r6_17_opt_in_us_cache_preview_plan.md)
- Blockers: [docs/66_r6_17_pre_implementation_review_pack.md](../docs/66_r6_17_pre_implementation_review_pack.md) §0 — `return_1d` · `volume_status` · freshness gate **before** preview section

## 許可 scope

- read-only cache / inventory 読み取り
- opt-in CLI flag（明示フラグのみ）
- markdown プレビュー節（opt-in 時のみ）
- tests + docs（実装範囲内）
- PR 作成 · CI 確認

## 禁止（`.agent/standard_clauses.md` に加えて）

- live HTTP · cache write
- workflow / Makefile / `pyproject.toml` 変更（明示承認なし）
- daily / signals **default** 変更
- portfolio / macro / Veto 接続
- 売買推奨・自動 instruction
- R6.17 以外のフェーズ混在
- main direct push · force push · branch/worktree 削除

## Sound policy

`.agent/standard_clauses.md` の Sound / notification policy に従う。

## 自走ルール

- 低リスク: ヘルパー・テスト・docs は一括可
- default パスに触れる変更は **停止** → `decisions needed`
- CI 同一原因 2 回 fail で停止
- 最終報告: `.agent/report_template.md`（単一コードブロック）

## Stages

1. State確認 · `origin/main` 同期
2. 設計質問（docs/65 §5）の回答を State Capsule に記載
3. read-only loader（必要最小）
4. opt-in flag + preview section
5. tests（opt-in only · no `.env` 依存）
6. PR 作成 · CI
7. **merge しない**（承認待ち）

## Architecture quality gate

実装前/PR前に **Claude Code**（`.agent/claude_arch_review_template.md`）で確認:

- default パス不変
- stale 扱い
- output contract
- rollback（flag off = 現状復帰）

## Final report format

`.agent/report_template.md` — merge 欄は **not performed unless authorized**。
