# Phase 0-v1.1 完了レポート

記録日時の目安: Phase 0-v1.1 クローズ時点（Observation Only + Shadow Portfolio の方針維持）。

## 1. Phase 0-v1.1 の完了条件

次を満たすことを完了条件とした。

- **プロジェクト骨格**: `pyproject.toml`、`src/invis_alpha_os/`、テスト、設定、ドキュメント、CI が揃い、`make test` / `make verify` で再現可能な状態であること。
- **CLI**: 正式名は `alpha-os`（ローカル検証・CI では `python -m invis_alpha_os.cli.main` 経由でも動作すること）。
- **Observation Only**: 自動売買・注文 API は実装しない。**No Auto Trading**。
- **Shadow Portfolio**: 「影のポートフォリオ」用の器を用意し、運用方針として明記する。
- **Evidence / data_confidence**: モデルおよび設定（`config/data_confidence.yaml` 等）で将来拡張可能な形にする。
- **Risk（Aegis の器）**: `hard_veto` / `soft_veto`（および `fomo_veto` の定義枠）と stub 実装。
- **データ層**: `MarketDataAdapter` 抽象、`yfinance` は fallback/prototype、`EDINET` / `SEC` はメタデータ想定の stub。
- **outputs**: 実行生成物は原則ローカル専用。**Git 管理は `.gitkeep` 等の最小限**に限定。
- **機密**: `.env` / credentials / token はリポジトリに含めない。
- **CI**: GitHub Actions の `tests` がグリーンになり、import エラーがないこと。

## 2. 実際に完了した項目

| 領域 | 内容 |
|------|------|
| パッケージ | `invis_alpha_os`、機能名ディレクトリ（`data/` `signals/` `risk/` `portfolio/` `observation/` 等） |
| CLI | `alpha-os` スクリプト + `python -m invis_alpha_os.cli.main` で `status` / `config-check` / `daily` / `pack` / `risks` / `snapshot` / `log` / `debug` |
| 確認手順 | `make verify`（`PYTHON=python` で CI でも実行可能） |
| 設定 | `config/` 配下の watchlist・veto・weights・market_data・data_confidence 等 |
| ドキュメント | システムマップ、命名、Observation プロトコル、スコープ、アイデアバックログ |
| outputs | `outputs/**` は ignore、`.gitkeep` でディレクトリ維持 |
| CI | `.github/workflows/tests.yml`：`make test` + `PYTHON=python make verify` |
| データパッケージ | `src/invis_alpha_os/data/` を Git 管理し、CI で `invis_alpha_os.data` import 解消 |

## 3. 発生した問題と対応

### 3.1 `alpha-os` の PATH 問題

- **問題**: 仮想環境を有効化していない環境では、`alpha-os` が `PATH` に無く `command not found` になる。
- **対応**: `Makefile` の `verify` および各ターゲットで **`$(PYTHON) -m invis_alpha_os.cli.main`** を優先。`make verify` はパス非依存で動かす方針。

### 3.2 outputs の Git 管理方針

- **問題**: 実行生成物（Markdown / JSONL 等）がコミット候補に混ざり、個人情報や実データの混入リスクがある。
- **対応**: `.gitignore` で `outputs/**` を無視し、**`!outputs/**/.gitkeep`** でディレクトリのみ維持可能に。README に「原則ローカル・Git 管理外」を明記。

### 3.3 GitHub Actions の Python バージョン

- **問題**: Python 3.14 を指定した際、`setup-python` やランナーとの相性で不安定・失敗する可能性があった。
- **対応**: CI 上の `python-version` を **3.12** 等、Actions で安定して提供されるバージョンに調整。ローカルは 3.14 の `.venv` でも `make verify` 成功を確認。

### 3.4 `src/invis_alpha_os/data/` が未追跡だった問題

- **問題**: `.gitignore` の `data/` が **任意深度**の `data` ディレクトリにマッチし、`src/invis_alpha_os/data/` が無視され、CI で `ModuleNotFoundError: No module named 'invis_alpha_os.data'`。
- **対応**: ルートのみ無視する **`/data/`** に変更し、`src/invis_alpha_os/data/` パッケージをコミット対象に戻した。

### 3.5 その他（参考）

- Actions ログ UI に **「Oh hello」「Made with ❤️ by humans.txt」** 等が表示されるケースがあるが、**リポジトリ内に該当文字列が無いことを確認**。UI 側表示と判断。

## 4. 現在の安全運用ルール

- **outputs**: 原則 **Git 管理外**。実行結果はローカルのみ。.gitkeep 以外はコミットしない。
- **機密**: **`.env` / `credentials.json` / `token.json` / API キーはコミット禁止**（`.gitignore` と運用で二重チェック）。
- **No Auto Trading**: 自動発注・ブローカー連携は Phase 0 では行わない。
- **Observation Only + Shadow Portfolio**: 観察と記録、影ポートフォリオの枠を中心に運用。**初めての数週間はレビュー前提**でボット出力を扱う（README に準ずる）。

## 5. 次フェーズ Phase 1a の候補

優先順位は未固定。検討用のバックログとして置く。

- **watchlist.yaml 整備**（JP / US tier 構造の運用ルールと同期）
- **J-Quants 接続準備**（認証・レート制限・ストア設計、まだ本格取引なし）
- **日本株の価格・騰落率・出来高サージ取得の設計**（`MarketDataAdapter` の日本株実装方針）
- **daily report への「日本株 signal」枠の追加**（Phase 0 の dummy 出力から、設計済みフィールドのみ拡張）

---

関連: [01_development_status.md](./01_development_status.md)、[05_observation_protocol.md](./05_observation_protocol.md)
