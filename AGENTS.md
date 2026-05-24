# AGENTS.md — 汎用 AI エージェント向け指示書(invest-alpha-os)

版: v0.1 / 最終更新: 2026-05-23

このファイルは ChatGPT / Codex / Cursor が invest-alpha-os で作業する際の指示書。
Claude Code 専用指示は `CLAUDE.md` を参照する。

## 3行サマリー
- すべての作業前に `RULES.md` と `STATE.md` を読むこと。
- 投資ロジック(`signals/` / `risk/` / `portfolio/`)を Ops 基盤(`operator/`)より優先すること。
- 不確実な点は推測せず、`[要確認]` ラベルで明示すること。

## §1. 作業前の必須読み込み

作業開始時に必ず以下を読み、「`RULES.md` と `STATE.md` を読みました」と宣言してから着手すること。

1. `RULES.md` — ハード制約・禁止事項・出力形式
2. `STATE.md` — 現状スナップショット
3. `docs/decisions/` 内の直近3ファイル — 最近の戦略判断

`RULES.md` と他ファイルが矛盾する場合は、作業を止めて矛盾内容をユーザーに報告する。

## §2. 応答形式

- 応答冒頭に `[TERMINAL ACTION REQUIRED]` または `[AGENT-ONLY]` を明記する。
- 長文出力はMDファイル化し、チャット本文は結論・確度・リンク・次アクションだけに絞る。
- 進捗表示はドメイン別%で行う。単一の総合%は禁止。
- ターミナルコマンドを出す場合は、コメント行なしの単一bashブロックにまとめる。
- テスト実行は原則 `.venv/bin/python -m pytest` を使う。

## §3. ツール別の追加指示

### ChatGPT

- このプロジェクトでは最初に `RULES.md` / `AGENTS.md` / `STATE.md` を読む。
- 重要な戦略判断は `docs/decisions/YYYY-MM-DD_<topic>.md` への追記案として出す。
- 長文のLongpack、State Capsule、レビュー結果、テストレポートはMDファイルとして作る。
- ユーザーが「覚えて」と言った内容は、利用可能な継続記憶またはSSoTファイルへの反映案として提示し、ユーザー確認を求める。

### Codex(ChatGPT 内コードレビュー)

- コードレビュー時は `RULES.md` §2 のコード品質原則を採点基準にする。
- レビュー結果は `reports/YYYY-MM-DD/codex_review_<task>.md` 形式で出す。
- `BLOCKER` / `SHOULD_FIX_BEFORE_MERGE` / `NICE_TO_HAVE` / `DEFERRED_OPS_FREEZE` に分類する。
- Ops増築につながる提案は、product/safety-criticalでない限り `DEFERRED_OPS_FREEZE` に分類する。

### Cursor(AUTO / Composer 2)

- `.cursor/rules/main.mdc` を自動読み込みルールとして扱う。
- **ロングラン自律開発**: `.agent/cursor_agent_quality_efficiency_longrun_standard.md` に従う（PR粒度・テスト標準・P10 preflight・Final Report 形式）。
- 多ファイル編集前に `git status --short` を確認する。
- 未コミット変更がある場合は、作業開始前にユーザーへ報告する。
- Composer 2 使用時は、事前に Settings → Billing で spend limit を確認する。

## §4. ファイル更新ルール

- `RULES.md` の変更はユーザー承認なしに不可。
- `AGENTS.md` / `CLAUDE.md` / `.cursor/rules/main.mdc` の変更もユーザー承認なしに不可。
- `STATE.md` はAIが更新案を作成し、ユーザー承認後にコミットする。
- `docs/decisions/` への新規追加は、戦略判断・設計判断が発生した日に行う。
- 過去のdecisionファイルは原則immutableとし、取り消しは新しいdecisionで記録する。

## §5. 矛盾検知時の対応

`RULES.md` / `docs/decisions/` / `STATE.md` / `AGENTS.md` の間で矛盾を発見した場合、以下の順で対応する。

1. 矛盾内容を1行で明示する。
2. 優先順位に従う候補解を提示する。
3. ユーザー判断を待つ。

優先順位:

1. ユーザー直接指示
2. `RULES.md`
3. 最新の `docs/decisions/YYYY-MM-DD_*.md`
4. `STATE.md`
5. `AGENTS.md` / `CLAUDE.md` / `.cursor/rules/main.mdc`

## §6. 禁止事項の要約

以下は明示承認なしに実行しない。

- main直push
- force push
- branch/worktree削除
- live HTTP / cache write
- Gmail送信
- secrets / `.env` / token出力
- daily / signals default behavior変更
- `pyproject.toml` / `Makefile` / `.github/workflows/*` 変更
- GitHub auto-merge設定
- trading recommendation wording追加

## §7. このファイルへの追加履歴

- 2026-05-24: Cursor longrun standard 参照追加（`.agent/cursor_agent_quality_efficiency_longrun_standard.md`）
- 2026-05-23: 初版作成
