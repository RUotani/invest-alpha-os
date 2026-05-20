# R7.0-Ops-A: 自律ローカルrunner基盤

## 目的

invest-alpha-os の開発を、人間の細かい承認・手動コマンド貼り付け中心から、機械的な安全ゲートとcheckpointを持つ自律ローカルrunner中心へ移行する。

今回作るものは、今後の長時間処理・データ取得・レポート生成・証跡作成を安全に継続実行するための基盤。

このフェーズでは、実データの大量取得ではなく、以下を優先する。

- task YAMLを読む
- safety policy YAMLを読む
- dry-runを標準にする
- checkpointを作る
- evidence summaryを作る
- live HTTP / cache writeは明示ゲートがない限り拒否する
- 400/429/secrets/禁止文言/想定外ファイル変更で停止できる構造にする
- testsで安全性を確認する

## 現在状態

- latest main: `2a36e1b`
- R7.0-C1: main反映済み
- JP discovery: Core50 40/50、`discover-jp`あり
- US discovery: `discover-us` MVPあり
- JP/US共通契約: `discovery.cross_market.v1`
- Gmail: 日本語ナラティブ本文、`.md`添付なし、07:00 launchd設定済み

## 安全ルール

禁止:

- secrets / `.env` / API keys / credentials / token の出力
- credentials / token / env ファイルのcommit
- cache JSONのcommit
- live HTTPの無ゲート実行
- cache writeの無ゲート実行
- daily/signals default変更
- 売買推奨、投資助言、発注指示、目標株価、資産配分
- portfolio / macro / Veto / trading recommendation 接続
- force push
- branch / worktree削除
- main direct push
- full diff / full file / full pytest log / full CI log の貼付け

許可:

- source / tests / docs / ops配下の変更
- dry-run runner実装
- task YAML追加
- safety policy YAML追加
- checkpoint/evidence summary生成
- tests追加
- docs追加

## 実装方針

### 1. 既存構造確認

全文貼り付けは禁止。小さな検索結果だけ確認する。

```bash
rg -n "discover-jp|discover-us|jquants|cache|yaml|operator|runner|argparse|typer|subcommand" src tests config docs -g '!outputs/**' | head -160
find src/invis_alpha_os -maxdepth 3 -type f | sort | sed -n '1,160p'
find ops -maxdepth 3 -type f 2>/dev/null | sort | sed -n '1,120p'
```

### 2. 最小MVPスコープ

- `ops/runner/` または `src/invis_alpha_os/operator/` に dry-run runner
- `config/operator_runner_policy.yaml` — 停止条件・禁止パス・ゲート
- `config/tasks/` にサンプル task YAML（discovery read-only smoke 等）
- checkpoint: `outputs/operator/runner/<task_id>/<run_id>/checkpoint.json`（ローカルのみ・未コミット）
- evidence: `evidence_summary.json` + 短い Markdown
- CLI: `operator-runner run --task <path> [--dry-run]`（default dry-run）

### 3. 停止条件（policy-driven）

- `CONFIRM_LIVE_HTTP=YES` なしで live HTTP ステップ → stop
- `CONFIRM_CACHE_WRITE=YES` なしで cache write ステップ → stop
- HTTP 400/429 検出（ステップ結果に記録）→ stop
- forbidden output terms（discovery contract 再利用）
- git dirty paths が allowlist 外 → stop（dry-run では warn のみ可）

### 4. テスト

- policy YAML ロード
- dry-run が live/cache write を実行しない
- checkpoint / evidence ファイル生成（tmp_path）
- ゲート不足で RunnerStop

### 5. docs

- `docs/98_r7_0_ops_a_autonomous_local_runner.md`
- `docs/01` 追記

## 完了条件

- [ ] task + policy YAML 読み込み
- [ ] dry-run デフォルト
- [ ] checkpoint + evidence summary
- [ ] live HTTP / cache write 無ゲート拒否
- [ ] tests green
- [ ] docs 記録
- [ ] outputs/ 未コミット
