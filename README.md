## Laputa Alpha OS (InvisAlphaOS / invest-alpha-os)

個人投資家向けの **長期運用型 投資判断支援OS**。

Phase 0-v1.1 は **Observation Only**（執行・発注なし）で、将来の拡張（高品質データ、Shadow Portfolio、Outcome Log、Data Confidence、Hard/Soft Veto、US Watchlist Tier 制）に耐えるプロジェクト骨格を優先して構築します。

### Current Mode

- Current Mode: Observation Only + Shadow Portfolio
- No Auto Trading
- Bot output is for observation and review only during the first 12 weeks
- Do not commit `.env`, `credentials.json`, `token.json`, API keys

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

### 一括検証

初回セットアップ後の動作確認は、以下のいずれかで実行できます。

- 通常確認コマンド: `make verify`
- 仮想環境を明示する安全な確認コマンド: `PYTHON=.venv/bin/python make verify`

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

### セキュリティ

- **APIキー・token・credentials・`.env` は絶対にコミットしません**（`.gitignore` 済み）。
- データはローカル（`data/`）に保存し、Phase 0 では外部API連携は stub / prototype 扱いです。
- `outputs/` は原則ローカル実行結果として扱い、実データ・個人情報保護のため Git 管理外とします。

