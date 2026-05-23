# Development Automation Contract

## 目的

このリポジトリの開発では、単発の小さな実装指示ではなく、人間の手間を最小化しながら、安全に長距離で開発を進めることを基本方針とする。

## 基本骨格

1. 目的定義
2. Automation Contract 確認
3. 安全境界の固定
4. 人間の介入ポイント最小化
5. 30分 smoke
6. 3h productive run
7. 8h / 12h long-run
8. evidence / CI / PR / State Capsule 整備
9. 次フェーズ判断

## 自律開発レベル

- 低リスク作業は、細切れに確認せずまとめて進める。
- 1タスク/1PRで止まる設計を避ける。
- Cursor / Claude / Codex / Terminal を使って、複数タスク・複数PRを安全に進める。
- 人間の役割は原則として「開始」「危険操作の明示承認」「merge判断」に限定する。

## 許可する操作

- read-only調査
- docs更新
- tests追加・修正
- dry-run
- local evidence生成
- CI確認
- PR作成
- State Capsule作成
- Longpack作成

## 禁止する操作

- main direct push
- force push
- branch deletion
- worktree deletion
- secrets / .env / credentials / tokens の出力
- secrets / cache JSON / outputs のcommit
- 明示ゲートなしのlive HTTP
- 明示ゲートなしのcache write
- 明示ゲートなしのGmail send
- auto-merge
- trading recommendation / buy / sell / target price / allocation wording
- daily/signals default変更
- Veto / portfolio / macro のdefault接続

## 停止条件

以下の場合は停止して報告する。

- working treeが想定外にdirty
- 禁止path変更
- secrets疑い
- CI失敗
- test失敗
- PR作成失敗
- live HTTP / cache write / Gmail send など高リスク操作が必要
- force push / branch削除 / main push が必要
- 人間判断が必要なmerge判断

## 成功条件

各runでは、以下をできるだけ満たす。

- 実行時間またはタスク数の目標を明示
- 複数タスクをqueue化
- テスト実行
- CI確認
- evidence出力
- PR URL記録
- failed / skipped task分類
- 次回継続用 State Capsule 更新

## 出力ルール

- 巨大な指示はチャット本文ではなく `.md` ファイルに保存する。
- Cursor / Claude / Codex向けLongpackには、目的・安全ルール・停止条件・テスト・CI・最終報告形式を含める。
- agent最終報告は、ワンクリックで全文コピーできる単一Markdownブロックで返す。
- チャット本文は軽くし、判断・次アクション・ファイルパスを中心にする。

## 標準フロー

### Phase 0: setup

- repo状態確認
- branch確認
- open PR確認
- CI確認
- dirty tree確認
- safety boundary確認

### Phase 1: smoke

- 20〜30分程度
- 1〜2タスク
- 1PRまで
- CI確認
- evidence確認

### Phase 2: productive run

- 3時間程度
- 複数タスク
- 複数PR
- 失敗分類
- 継続/停止判断

### Phase 3: long-run

- 8h / 12h
- min runtime
- heartbeat
- queue exhaustion handling
- post-run review
- merge helper
- State Capsule作成

## 重要方針

機能を作る前に、まず開発を安全に回す仕組みを作る。
小さな手作業を積み上げるのではなく、低リスク作業を自律開発queueへ流し込む。
