## Laputa Alpha OS (InvisAlphaOS / invest-alpha-os)

個人投資家向けの **長期運用型 投資判断支援OS**。

Phase 0-v1.1 は **Observation Only**（執行・発注なし）で、将来の拡張（高品質データ、Shadow Portfolio、Outcome Log、Data Confidence、Hard/Soft Veto、US Watchlist Tier 制）に耐えるプロジェクト骨格を優先して構築します。

### Current Mode

- Current Mode: Observation Only + Shadow Portfolio
- No Auto Trading
- Bot output is for observation and review only during the first 12 weeks
- Do not commit `.env`, `credentials.json`, `token.json`, API keys

### Phase 1a — J-Quants（Task 1 & 2）

- **既定**: **`JQUANTS_ENABLED=false`** かつ **`JQUANTS_ALLOW_LIVE_HTTP=false`**。`make verify`・`daily`・`pack`・`risks` は **J-Quants へ接続しない**。
- **Task 2**: **`JQuantsClient`**（real-mode skeleton + **二重ゲート**）。
  - **`debug jquants-status`**: **HTTP 禁止**（状態フラグと `token_preview: "***"` のみ）。
  - **`debug jquants-daily-quotes`**: **既定は dry-run**。**実 HTTP** は **`--live` と `JQUANTS_ALLOW_LIVE_HTTP=true` の両方**が必要。
- **AI Agent に認証情報を渡さない**。`.env.example` は **変数名のみ**。
- 計画書: [docs/08_phase1a_jquants_plan.md](docs/08_phase1a_jquants_plan.md)

### クイックスタート

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
alpha-os --help
```

### Phase 0 の基本コマンド

- `alpha-os status`
- `alpha-os config-check`
- `alpha-os daily`
- `alpha-os pack --ticker 7011`
- `alpha-os risks`
- `alpha-os snapshot watchlist`
- `alpha-os snapshot shadow-portfolio`
- `alpha-os log outcome`
- `alpha-os debug adapters`
- `alpha-os debug jquants-status`（HTTP なし）
- `alpha-os debug jquants-daily-quotes --code ... --from-date ... --to-date ... [--live]`

### 一括検証

初回セットアップ後の動作確認は、以下のいずれかで実行できます。

- 通常確認コマンド: `make verify`
- 仮想環境を明示する安全な確認コマンド: `PYTHON=.venv/bin/python make verify`
- **`make codex-review`**: `codex exec`（read-only）でレビューし結果を `.ai/reviews/latest.md` へ。**`.ai/reviews/*.md` は Git 無視**。
- **`make ai-check`**: `make verify` → `codex-review` → `git status`。`Makefile` はデフォルト `PYTHON=python` のとき `.venv/bin/python` があればそちらへ寄せます（明示した `PYTHON=...` は尊重）。

```bash
make verify
```

`make verify` は以下を順番に実行し、エラー時はその場で停止します。

- tests
- status
- config-check
- snapshot watchlist
- daily
- pack --ticker 7011
- risks
- git status --short

### AI 開発運用（Phase 0 完了後）

複数の AI / ツールと協働する際の役割分担と標準フローは [docs/07_ai_development_workflow.md](docs/07_ai_development_workflow.md) を参照してください。

- **`git add` / `commit` / `push`** は **人間のレビューと明示承認のうえでのみ**行う。
- `.env`、`credentials.json`、`token.json`、`outputs/` の実行生成物（実データ）は **Git 管理しない**（セキュリティ節とも整合）。

#### Codex レビュー（半自動）

- **`make codex-review`**: Codex CLI（`codex exec`・read-only サンドボックス・非対話）でレビューし、結果を `.ai/reviews/latest.md` に保存。`.env` は参照しない。このファイル種別は `.gitignore` で **コミット対象外**。
- **`make ai-check`**: `PYTHON` を **`make verify` に明示的に渡し**、その後 `codex-review` と `git status --short` を実行。

Codex 未インストール時は `codex-review` が **親切なスキップメッセージ**で終了（`make` は続行できる）します。

### セキュリティ

- **APIキー・token・credentials・`.env` は絶対にコミットしません**（`.gitignore` 済み）。
- データはローカル（`data/`）に保存し、Phase 0 では外部API連携は stub / prototype 扱いです。
- `outputs/` は原則ローカル実行結果として扱い、実データ・個人情報保護のため Git 管理外とします。

