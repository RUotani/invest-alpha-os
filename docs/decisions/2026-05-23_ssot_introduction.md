# SSoT導入の決定

日付: 2026-05-23
ステータス: approved
関連ファイル: `RULES.md`, `AGENTS.md`, `CLAUDE.md`, `STATE.md`, `.cursor/rules/main.mdc`, `docs/decisions/README.md`

## 3行サマリー
- invest-alpha-os のAIツール間情報断絶を解消するため、repo内SSoTを導入する。
- `RULES.md` をハード制約、`STATE.md` を現状、`docs/decisions/` を判断ログとして扱う。
- ChatGPT / Cursor / Claude Code / Codex は、各作業開始時にSSoTファイルを読む。

## 結論(1〜3行)

- invest-alpha-os では、複数AIツール間の記憶断絶を解消するため、repo内にSingle Source of Truthを置く。
- Phase 1では `AGENTS.md` / `CLAUDE.md` / `.cursor/rules/main.mdc` / `STATE.md` / `docs/decisions/README.md` / 本decisionを作成する。
- `RULES.md` は既存のハード制約として参照のみ行い、ユーザー承認なしに変更しない。

## 確度

- 95%

## 背景

invest-alpha-os 開発では ChatGPT、Cursor、Claude Code、Codex を併用している。
各ツールが独立した文脈を持つため、以下の問題が発生していた。

- 同じ説明を何度も繰り返す必要がある。
- 古い指示ほど効かなくなる。
- ツール間で「前のセッションで決めたこと」が伝わらない。
- LongpackやState Capsuleがチャット内に散在し、参照性が低い。
- Ops増築と投資ロジック優先の判断がぶれやすい。

## 検討した選択肢

1. ChatGPTのメモリやProject Instructionsだけに依存する。
2. 各AIツールごとに個別ルールを持つ。
3. repo内にSSoTファイル群を置き、全ツールが同じファイルを読む。
4. 自動生成スクリプトやCI検証まで含めたSSoT基盤をすぐ作る。

## 採用した選択肢の根拠

選択肢3を採用する。

- repo内ファイルであれば、ChatGPT / Cursor / Claude Code / Codex が同じ情報を参照できる。
- Gitで変更履歴が残る。
- チャット移行時もファイルを読むだけで文脈を復元しやすい。
- Phase 1は手動運用に限定し、過剰なOps基盤化を避けられる。
- `RULES.md` と整合し、Architecture Astronaut化を抑制できる。

## 反証(bear case)

この決定が誤りだった場合のシナリオ:

- SSoTファイル自体が肥大化し、読む側のAIが要点を取り違える。
- `STATE.md` が更新されず、古い情報を信じてしまう。
- decisionファイルが増えすぎ、検索性が下がる。
- SSoT維持が目的化し、投資ロジック実装より管理作業が増える。

再評価条件:

- SSoT更新作業が開発時間の20%以上を占める。
- 2回以上、古い `STATE.md` に起因する判断ミスが発生する。
- `operator/` や運用基盤の作業が再び連続し、投資ロジック実装が遅れる。

## 影響範囲

新規作成:

- `AGENTS.md`
- `CLAUDE.md`
- `.cursor/rules/main.mdc`
- `STATE.md`
- `docs/decisions/README.md`
- `docs/decisions/2026-05-23_ssot_introduction.md`

参照のみ:

- `RULES.md`

変更しない:

- `pyproject.toml`
- `Makefile`
- `.github/workflows/*`
- product code
- tests
- cache files
- outputs

## 次のアクション

- [ ] ユーザーが生成ファイルを確認する。
- [ ] `[要確認]` 項目を必要に応じて修正する。
- [ ] ファイルをrepoへ追加する。
- [ ] Cursor / Claude Code に `RULES.md` と `STATE.md` を読ませてSSoT機能を検証する。
- [ ] 今後の戦略判断は `docs/decisions/` に記録する。

## このファイルへの追加履歴

- 2026-05-23: 初版作成
