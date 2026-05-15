# R6.13-B — US report opt-in operational readiness

**ステータス**: 作業ブランチ `work/r6-13-b-us-report-opt-in-operational-readiness` のみ（**`main` 未反映**）。

---

## 1. 目的

- オペレータが **`daily --us-signals-dry-run-manifest`** を使うときの **再現可能な runbook** を固定する。
- invalid manifest／スキーマ不正時の **期待挙動**（**exit 0**・`_UNAVAILABLE` 相当の短文）が追試できる **smoke** を置く。

## 2. 非目的

- daily の **default** 変更 · config フラグ新設 · product の renderer／manifest contract の変更。
- live HTTP · production cache の書き込み · Veto／portfolio／macro 接続。
- stale branch の **削除**または **merge**（本項は説明のみ。整理は別タスク）。
- **`review_integrated_20260515.md` の運用混入**。

## 3. 前提（R6.12-E / R6.12-G / R6.13-A との関係）

- **flag 無し**: `daily` は従来どおり（US Dry Run **節なし**）。golden／regression で固定済み。
- **flag 有り**: 明示パスの manifest のみ評価（**自動キャッシュ走査なし**）。
- **invalid**: `append_us_signals_dry_run_section` が `_UNAVAILABLE` を返す経路 ⇒ 日報末尾に **`*(dry-run skipped: manifest_invalid)*`** が載り、CLI は **終了コード 0**。

## 4. Runbook（リポジトリルートから）

```bash
# ヘルプ（フラグ確認）
PYTHONPATH=src python -m invis_alpha_os.cli.main daily --help

# 既定の manifest fixture（単一検証パス）。dry-runのみ · 推奨例。
PYTHONPATH=src python -m invis_alpha_os.cli.main daily --us-signals-dry-run-manifest tests/fixtures/us_equities/us_cache_signals_batch_minimal.json
```

- **cwd**: **リポジトリルート**を推奨（相対パスは `ROOT_DIR` 基準で解決される想定）。
- **出力**: `outputs/reports/daily/<YYYY-MM-DD>.md`（JST は CLI 側の既定日付）。
- live HTTP：**使用しない**。cache：**読むだけ**（manifest の `cache_path` が指すローカル JSON／テストキャッシュのみ）。

### invalid manifest を置いたい場合の期待値

| 入力例 | CLI exit | US 節見出し | 本文 |
|---|---|---|---|
| パース不能 JSON／欠損ファイル | 0 | `### US Signals Dry Run (opt-in)` | `*(dry-run skipped: manifest_invalid)*` と `live_http: false` |
| 正しい JSON だが **`entries`: 空** などスキーマ不一致 | 0 | 同上 | 同上 |
| manifest 無し実行 | 0 | **なし** | 変更なし（R6.12-E regression） |

## 5. Smoke（自動）

- **`tests/test_us_report_opt_in_operational_readiness.py`**
  - `--help` に `--us-signals-dry-run-manifest` が出ること（**subprocess の `python -m invis_alpha_os.cli.main …` と `PYTHONPATH`=`src` 相当で確認し、CLI runner／Rich の表示幅問題を避ける）。
  - **`cwd = REPO_ROOT`** で runbook と同じ相対パス文字列が通ること。
  - `entries: []` のような **構文は正しいが manifest 無効** のケースで **exit 0**＋短文 skip。

## 6. 将来リスク（手動チェックリスト）

| リスク | 緩和 |
|---|---|
| manifest の typo／相対パス誤り | §4 の単一 canonical fixture でまず確認 |
| dry-run を「売買推奨」と誤解 | 出力の **not buy/sell advice** 文言を運用側で明示 |
| PDF／Gmail 表幅崩れ | 本タスク対象外。出力整形は別レビュー |
| stale worktree が増殖 | **[docs/01_development_status.md](./01_development_status.md)** のメモのみ（削除は別決定） |

## 7. 次候補

- **R6.13-C** または **R6.14**: integrated golden と runbook を跨ぐ縮約・PDF 配慮、`make`/`CI` での明示ターゲット化（**本ブランチでは Makefile／workflow は触らない**）。
