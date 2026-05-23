# docs/decisions/ — 戦略判断の immutable ログ

版: v0.1 / 最終更新: 2026-05-23

## 3行サマリー
- 戦略判断・設計判断を時系列で記録するためのディレクトリ。
- 新しいAIセッション開始時に直近decisionを読み、文脈を継承する。
- approved後のdecisionは原則変更せず、修正は新decisionで記録する。

## 目的

- 戦略判断・設計判断を時系列で記録し、後から検索・参照可能にする。
- AIツールが新セッション開始時に直近の判断を読み、文脈を継承できるようにする。
- 判断の根拠と反証を併記し、後の再評価を可能にする。
- 「前のチャットで決めた」情報を、チャット記憶ではなくrepo内ファイルで検証可能にする。

## ファイル命名規則

`YYYY-MM-DD_<topic_snake_case>.md`

例:

- `2026-05-23_ssot_introduction.md`
- `2026-05-23_operator_runner_freeze.md`
- `2026-05-23_terminal_first_supervised_run.md`

## 各ファイルのテンプレート

```markdown
# <タイトル>

日付: YYYY-MM-DD
ステータス: proposed / approved / superseded
関連ファイル: <他の decisions ファイルや RULES.md セクション>

## 結論(1〜3行)
- ...

## 確度
- XX%

## 背景
- 何が問題だったか

## 検討した選択肢
1. ...
2. ...
3. ...

## 採用した選択肢の根拠
- ...

## 反証(bear case)
- この決定が誤りだった場合のシナリオ
- どんな状況なら再評価すべきか

## 影響範囲
- 変更されるファイル
- 影響を受ける他の判断

## 次のアクション
- [ ] ...
- [ ] ...
```

## immutability ルール

- 一度 `approved` になったファイルは原則変更しない。
- 取り消し・修正が必要な場合は、新ファイルで `supersedes` / `superseded by` を明記する。
- 古いファイルを直接書き換えると、AIツールが過去判断を誤認する原因になる。
- 誤字・リンク切れなど意味を変えない修正のみ例外として許容する。

## decisionを作るタイミング

以下のいずれかに該当する場合、decisionファイルを作る。

- 30分以上の議論で戦略判断が固まった。
- 複数AIツールにまたがって共有すべき運用ルールが決まった。
- プロジェクト優先順位が変わった。
- 既存ルールの例外を認めた。
- 主要な設計方針を採用・却下した。
- 新Chatへ移行する前に文脈を固定する必要がある。

## 検索用語ガイド

AIツールが過去の判断を探すときは、以下のキーワードでgrepする。

- `operator-runner` / `Ops` / `Architecture Astronaut`
- `signals` / `momentum` / `peer_sync` / `veto_rules`
- `observation_log` / `forward validation` / `veto-at-t`
- `US 30+` / `tier-1 refresh` / `cache-only`
- `SSoT` / `RULES.md` / `STATE.md`
- `Terminal-first` / `Longpack` / `supervised run`

## このファイルへの追加履歴

- 2026-05-23: 初版作成
