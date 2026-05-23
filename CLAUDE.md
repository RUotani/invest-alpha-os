# CLAUDE.md — Claude Code 専用指示書(invest-alpha-os)

版: v0.1 / 最終更新: 2026-05-23

このファイルは Claude Code が invest-alpha-os の作業を始める際に最初に読むファイル。
Anthropic の Claude Code 慣習に従い、リポジトリ直下に配置する。

## 3行サマリー
- 作業前に `RULES.md` と `STATE.md` を必ず読む。
- 優先順位は `signals/` > `risk/` > `portfolio/` > `data/` > `reports/` > `operator/`。
- Architecture Astronaut 検知を常時有効にし、Ops増築より投資ロジック実装を優先する。

## §1. プロジェクト概要

- invest-alpha-os は投資判断支援OSであり、現在は observation-only モードを原則とする。
- 主要領域は `signals/`、`risk/`、`portfolio/`、`data/`、`reports/`、`operator/`。
- 直近の主戦場は、US cache-only signals、forward-return validation、observation_log、weekly/daily report usefulness。
- trading recommendation、order execution、自動売買は対象外。

## §2. 作業開始時の必須手順

1. `RULES.md` 全文を読む。
2. `STATE.md` 全文を読む。
3. `docs/decisions/` 内の最新3ファイルを読む。
4. 「`RULES.md` と `STATE.md` を読みました」と宣言する。
5. 作業範囲・禁止事項・変更予定ファイルを簡潔に提示してから着手する。

## §3. 設計レビュー時の出力形式

- 結論を最初に、確度(%)付きで提示する。
- 反証セクション(bear case / disconfirming evidence)を必ず含める。
- 不明点は `[要確認]` で明示する。
- ドメイン別進捗を表示する。単一総合%は禁止。
- レビュー指摘は以下に分類する。
  - `BLOCKER`
  - `SHOULD_FIX_BEFORE_MERGE`
  - `NICE_TO_HAVE`
  - `DEFERRED_OPS_FREEZE`

## §4. 投資ロジック作業時の特別ルール

- `signals/` / `risk/` / `portfolio/` に関わる作業を最優先する。
- `operator/` の追加機能は、投資ロジック実装を直接阻害する問題の解消に限定する。
- 銘柄コード正規化は4桁数字限定にしない。日本株の英字含む5桁コード、例 `285A`、を必ず通す。
- 新規関数には type hints を付ける。
- 正常系だけでなく失敗系テストを最低1件含める。
- マジックナンバーは定数化またはconfig化する。
- printデバッグを残さず、必要な場合はloggingを使う。

## §5. 触ってはいけないファイル・操作

明示承認なしに以下を変更・実行しない。

- `pyproject.toml`
- `Makefile`
- `.github/workflows/*`
- `.env` / secrets / credentials関連
- main直push
- force push
- branch/worktree削除
- live HTTP / cache write
- Gmail送信
- GitHub auto-merge設定
- daily / signals default behavior変更
- trading recommendation関連コード

## §6. 長時間runの条件

長時間runは、以下をすべて満たす場合のみ許可される。

- キューの60%以上が `signals/` / `risk/` / `portfolio/` 関連。
- 時間枠を埋めることが目的化していない。
- `operator/` 系PRが連続していない。
- Architecture Astronaut検知を有効にする。
- 実行前にキュー構成比を提示し、ユーザー承認を得る。

条件を満たさない場合は、短時間run + 人間レビューへ切り替える。

## §7. Final Report形式

Final Reportは単一Markdownコードブロックで返す。

必須項目:

- 結論
- Main state
- Completed product work
- Changed files
- Tests
- Review classification
- Safety
- Open PRs / CI
- Human merge commands
- Next product actions

## §8. このファイルへの追加履歴

- 2026-05-23: 初版作成
