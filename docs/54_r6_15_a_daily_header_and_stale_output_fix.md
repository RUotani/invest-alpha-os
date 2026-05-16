# R6.15-A — Daily report header wording and stale future outputs

**ステータス**: **ブランチ作業のみ**（**`main` 未反映**）。ブランチ: **`work/r6-15-a-daily-header-and-stale-output-fix`**。**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-15-a`。外部レビュー **F-1 / F-2** への第一段対応。

---

## 1. 目的

- **F-1**：`alpha-os daily` 生成 Markdown の冒頭文言を現状（momentum cache 系セクションがあること）と整合させる。**表示文言のみ**変更。
- **F-2**：過去試験／バグ由来の **`2031-07-15`** 付けの **出力ファイルがローカルに残っていた場合**のみ、指定パスとして **削除**（**単一ファイル `rm`**。**`git worktree remove`** / **`rm -rf` は不使用**）。
- **`main`** および **Makefile / workflows / veto / US 既定接続には触れない**。

## 2. 非目的

- **`main` マージ**。**Pull Request**。**live HTTP**。**production cache write**。**Veto ルール変更**。**`include_us_momentum_cache_only_section` のデフォルト変更**。**worktree の追加削除**。**`review_integrated_*` のコミット**。**`git worktree remove`**。**`rm -rf`**。**`research pack`**（`alpha-os pack`）の体裁全面改稿（本タスクは **daily** のみ）。
- **`r6-10-g`** の修復／削除。

## 3. F-1（`daily()` ヘッダ）変更

**対象**: `src/invis_alpha_os/cli/main.py` の **`daily`** コマンド内、`report_body` 先頭の固定行。

**削除した旧文言**:

- `Phase 0 dummy report.`
- `- Observation only`
- `- No auto trading`
- （見出し直後にあった）`- Phase 1a stub`

**追加した新文言**:

- `Observation only — no auto trading.`
- 見出し `## Japan Signals — Momentum Cache`
- **`jq_line` / `jp_n` は維持**（順序のみ **Watchlist → J‑Quants 行**に整理）。

意図: **Momentum cache** が既定で続く構成とヘッダを揃える（**機能フラグには未変更**）。

## 4. 関連テスト

- **`tests/test_us_signals_report_opt_in.py`**：**`_GOLDEN_DAILY_BODY_NO_OPTS`** を新ヘッダに合わせる。
- **`tests/test_daily_japan_signals.py`** 等：**`## Japan Signals` / `Observation only`** は **`## Japan Signals — Momentum Cache`** および単一行ヘッダに **部分一致**で引き続き満たす。

## 5. F-2（stale future output）

**候補**:

- `outputs/reports/daily/2031-07-15.md`
- `outputs/research_packs/7011_2031-07-15.md`

**Git 状態**: **`outputs/` は `.gitignore` 対象**のため両方とも **tracked ではない**。存在した場合のみ **`rm`**（**単一ファイル**。**`git rm` 不要**）。

**実施結果**（本ワークツリー環境・記録時点）:

- **main の作業ツリー側**で両ファイルが **存在** → **`rm`**。
- **`invest-alpha-os-r6-15-a`** 側では、`7011` パックは **不在**。`daily` テスト生成の **`outputs/reports/daily/2031-07-15.md`** が一時作成されていた場合は **記録後に削除**。

## 6. アーキテクチャ確認

- **live HTTP**：追加なし  
- **cache write**：変更なし（**削除は生成物のみ**）。  
- **US opt-in**：既定・表示条件は変更なし。  

## 7. 次候補

- **R6.15-B**：`review_integrated_*` の扱い決定・整理（別承認）。  
- **R6.15-C**：US cache population runbook（別承認）。  
- **R6.14-J**：R12 single cleanup の継続（別承認）。  
